from abc import ABC, abstractmethod
import os
import logging
import aiofiles
import aioboto3
from uuid import uuid4
from fastapi import UploadFile, HTTPException, status
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class StorageProvider(ABC):
    """
    Architectural Interface for file storage.
    Enables swapping between Local and AWS S3 without breaking business logic.
    """
    @abstractmethod
    async def save_product_image(self, file: UploadFile, tenant_id: str, product_id: str) -> str:
        pass

class LocalStorageProvider(StorageProvider):
    """
    Production-ready local storage implementation with CDN (Cloudflare) caching support.
    """
    ALLOWED_EXTENSIONS = {"image/jpeg", "image/png", "image/webp"}
    BASE_UPLOAD_DIR = "uploads/products"

    async def save_product_image(self, file: UploadFile, tenant_id: str, product_id: str) -> str:
        if file.content_type not in self.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid file type. Only JPEG, PNG, and WEBP are allowed."
            )
        
        product_dir = os.path.join(self.BASE_UPLOAD_DIR, tenant_id, product_id)
        os.makedirs(product_dir, exist_ok=True)
        
        file_extension = file.filename.split(".")[-1]
        secure_filename = f"{uuid4().hex}.{file_extension}"
        file_path = os.path.join(product_dir, secure_filename)

        content = await file.read()
        async with aiofiles.open(file_path, "wb") as buffer:
            await buffer.write(content)
        
        return f"/static/products/{tenant_id}/{product_id}/{secure_filename}"

class S3StorageProvider(StorageProvider):
    """
    Cloud-native AWS S3 storage implementation using asynchronous I/O (aioboto3).
    """
    ALLOWED_EXTENSIONS = {"image/jpeg", "image/png", "image/webp"}

    def __init__(self):
        self.bucket = os.getenv("AWS_S3_BUCKET")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.session = aioboto3.Session(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=self.region
        )

    async def save_product_image(self, file: UploadFile, tenant_id: str, product_id: str) -> str:
        if file.content_type not in self.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid file type. Only JPEG, PNG, and WEBP are allowed."
            )

        file_extension = file.filename.split(".")[-1]
        secure_filename = f"{uuid4().hex}.{file_extension}"
        s3_key = f"tenants/{tenant_id}/products/{product_id}/{secure_filename}"

        try:
            async with self.session.client("s3") as s3_client:
                await s3_client.upload_fileobj(
                    file.file,
                    self.bucket,
                    s3_key,
                    ExtraArgs={"ContentType": file.content_type}
                )
            return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{s3_key}"
        except ClientError as error:
            logger.error(f"S3 Upload Error: {error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload image to cloud storage."
            )

# Active Storage Strategy: Dynamically injected based on environment variables.
# Ensures the application is Open for extension, but Closed for modification.
STORAGE_TYPE = os.getenv("STORAGE_TYPE", "local").lower()

if STORAGE_TYPE == "s3":
    StorageService = S3StorageProvider()
else:
    StorageService = LocalStorageProvider()