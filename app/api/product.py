from fastapi import APIRouter, Depends, HTTPException, Query, status, File, UploadFile
from sqlalchemy.orm import Session
from uuid import UUID
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.product import ProductCreate, ProductResponse
from app.schemas.pagination import PaginatedResponse
from app.services.product import ProductService
from app.services.storage import StorageService


router = APIRouter()

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product_in: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new product or restore a soft-deleted one if SKU matches.
    """
    product = ProductService.create(
        db=db, 
        product_in=product_in, 
        tenant_id=current_user.tenant_id,
        user_id=current_user.id
    )
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A product with this SKU already exists and is active."
        )

    return product


@router.get("/", response_model=PaginatedResponse[ProductResponse])
def list_products(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    name: str | None = Query(None, description="Filter by product name"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve a paginated list of products for the authenticated tenant.
    Includes optional search filters.
    """
    return ProductService.get_paginated_products(
        db=db,
        tenant_id=current_user.tenant_id,
        page=page,
        size=size,
        name_filter=name
    )

@router.post("/{product_id}/image", response_model=ProductResponse)
async def upload_product_image(
    product_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a main image for a specific product.
    Files are stored securely and linked to the product's database record.
    """
    image_url = await StorageService.save_product_image(file, str(current_user.tenant_id))
    
    updated_product = ProductService.update_image_url(
        db=db, 
        product_id=product_id, 
        tenant_id=current_user.tenant_id, 
        image_url=image_url
    )
    
    if not updated_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or access denied."
        )
        
    return updated_product

from fastapi import Response # Adicione no topo

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product_in: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new product or restore a soft-deleted one if SKU matches.
    """
    product = ProductService.create(
        db=db, 
        product_in=product_in, 
        tenant_id=current_user.tenant_id,
        user_id=current_user.id
    )
    
    # Se o Service devolveu None, é porque existe um produto ativo com esse SKU
    if not product:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A product with this SKU already exists and is active."
        )

    return product

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Soft-delete a product. It will be hidden from catalogs but retained in the database.
    """
    success = ProductService.delete(
        db=db,
        product_id=product_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or already deleted."
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)