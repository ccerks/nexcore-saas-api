from abc import ABC, abstractmethod
import os
import logging
import aiofiles
import aioboto3
from uuid import uuid4
from fastapi import UploadFile, HTTPException, status
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Magic bytes signatures for server-side file type validation.
# Prevents content-type spoofing attacks where a malicious file
# declares itself as image/png but carries executable content.
_MAGIC_SIGNATURES: dict[bytes, str] = {
    b"\xff\xd8\xff": "jpg",
    b"\x89PNG\r\n\x1a\n": "png",
    b"RIFF": "webp",  # RIFF....WEBP — checked with additional offset below
}
_ALLOWED_EXTENSIONS: frozenset[str] = frozenset({"jpg", "jpeg", "png", "webp"})
_ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset({"image/jpeg", "image/png", "image/webp"})
_MAGIC_BYTES_READ_SIZE = 12


def _detect_extension_from_magic(header: bytes) -> str | None:
    """
    Inspects the first bytes of a file to determine its true type,
    regardless of the declared Content-Type or filename extension.
    Returns a safe extension string, or None if unrecognised.
    """
    if header[:3] == b"\xff\xd8\xff":
        return "jpg"
    if header[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    # WEBP: bytes 0-3 are 'RIFF', bytes 8-11 are 'WEBP'
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "webp"
    return None


def _get_safe_extension(file_header: bytes, declared_content_type: str) -> str:
    """
    Returns a sanitised file extension validated against both magic bytes
    and the declared Content-Type header.
    Raises HTTPException 400 if either check fails.
    """
    if declared_content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only JPEG, PNG, and WEBP are allowed.",
        )

    magic_ext = _detect_extension_from_magic(file_header)
    if magic_ext is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content does not match a supported image format.",
        )

    return magic_ext


class StorageProvider(ABC):
    """
    Abstract interface for file storage backends.
    Enables swapping between Local and AWS S3 without modifying business logic (OCP).
    """

    @abstractmethod
    async def save_product_image(
        self, file: UploadFile, tenant_id: str, product_id: str
    ) -> str:
        pass


class LocalStorageProvider(StorageProvider):
    """
    Local filesystem storage implementation.
    Suitable for development and single-server deployments with a CDN (e.g. Cloudflare) in front.
    """

    BASE_UPLOAD_DIR = "uploads/products"

    async def save_product_image(
        self, file: UploadFile, tenant_id: str, product_id: str
    ) -> str:
        content = await file.read()

        # Server-side validation: inspect actual file bytes, not just the declared header.
        file_header = content[:_MAGIC_BYTES_READ_SIZE]
        safe_ext = _get_safe_extension(file_header, file.content_type)

        product_dir = os.path.join(self.BASE_UPLOAD_DIR, tenant_id, product_id)
        os.makedirs(product_dir, exist_ok=True)

        # Build filename exclusively from a UUID and the validated extension.
        # The original filename is intentionally discarded to prevent path traversal.
        secure_filename = f"{uuid4().hex}.{safe_ext}"
        file_path = os.path.join(product_dir, secure_filename)

        async with aiofiles.open(file_path, "wb") as buffer:
            await buffer.write(content)

        return f"/static/products/{tenant_id}/{product_id}/{secure_filename}"


class S3StorageProvider(StorageProvider):
    """
    Cloud-native AWS S3 storage implementation using asynchronous I/O (aioboto3).
    """

    def __init__(self) -> None:
        self.bucket = os.getenv("AWS_S3_BUCKET")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.session = aioboto3.Session(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=self.region,
        )

    async def save_product_image(
        self, file: UploadFile, tenant_id: str, product_id: str
    ) -> str:
        content = await file.read()

        # Server-side validation against magic bytes before any network I/O.
        file_header = content[:_MAGIC_BYTES_READ_SIZE]
        safe_ext = _get_safe_extension(file_header, file.content_type)

        secure_filename = f"{uuid4().hex}.{safe_ext}"
        s3_key = f"tenants/{tenant_id}/products/{product_id}/{secure_filename}"

        try:
            import io
            async with self.session.client("s3") as s3_client:
                await s3_client.upload_fileobj(
                    io.BytesIO(content),
                    self.bucket,
                    s3_key,
                    ExtraArgs={"ContentType": file.content_type},
                )
            return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{s3_key}"
        except ClientError as error:
            logger.error("S3 Upload Error: %s", error)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload image to cloud storage.",
            )


# Active Storage Strategy — resolved once at startup from the environment variable.
# Follows the Open/Closed Principle: extend by adding a new provider class, not by modifying this file.
_STORAGE_TYPE = os.getenv("STORAGE_TYPE", "local").lower()

if _STORAGE_TYPE == "s3":
    StorageService: StorageProvider = S3StorageProvider()
else:
    StorageService: StorageProvider = LocalStorageProvider()
