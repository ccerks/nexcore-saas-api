import os
import aiofiles
from uuid import uuid4
from fastapi import UploadFile, HTTPException, status

class StorageService:
    """
    Handles asynchronous file uploads and physical storage isolation.
    """
    ALLOWED_EXTENSIONS = {"image/jpeg", "image/png", "image/webp"}
    BASE_UPLOAD_DIR = "uploads/products"

    @staticmethod
    def _validate_image(file: UploadFile) -> None:
        if file.content_type not in StorageService.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid file type. Only JPEG, PNG, and WEBP are allowed."
            )

    @staticmethod
    async def save_product_image(file: UploadFile, tenant_id: str) -> str:
        """
        Validates, renames, and asynchronously saves the image to a tenant-specific directory.
        """
        StorageService._validate_image(file)
        
        tenant_dir = os.path.join(StorageService.BASE_UPLOAD_DIR, tenant_id)
        os.makedirs(tenant_dir, exist_ok=True)
        
        file_extension = file.filename.split(".")[-1]
        secure_filename = f"{uuid4().hex}.{file_extension}"
        file_path = os.path.join(tenant_dir, secure_filename)

        content = await file.read()
        async with aiofiles.open(file_path, "wb") as buffer:
            await buffer.write(content)
        
        return f"/static/products/{tenant_id}/{secure_filename}"