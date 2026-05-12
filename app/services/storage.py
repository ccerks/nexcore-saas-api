import os
import shutil
from uuid import uuid4
from fastapi import UploadFile, HTTPException, status

class StorageService:
    """
    Handles file uploads and storage. 
    Currently configured for local disk storage, but abstracted 
    to easily swap to AWS S3 or other Cloud Storage in the future.
    """
    ALLOWED_EXTENSIONS = {"image/jpeg", "image/png", "image/webp"}
    UPLOAD_DIR = "uploads/products"

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
        Validates, renames, and saves the uploaded image.
        Returns the relative URL path to access the image.
        """
        StorageService._validate_image(file)
        
        os.makedirs(StorageService.UPLOAD_DIR, exist_ok=True)
        
        file_extension = file.filename.split(".")[-1]
        secure_filename = f"{tenant_id}_{uuid4().hex}.{file_extension}"
        file_path = os.path.join(StorageService.UPLOAD_DIR, secure_filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return f"/static/products/{secure_filename}"