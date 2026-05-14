from fastapi import APIRouter, Depends, HTTPException, Query, status, File, UploadFile, Response, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from uuid import UUID
from typing import List

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductResponse
from app.schemas.pagination import PaginatedResponse
from app.services.product import ProductService
from app.services.storage import StorageService
from app.core.limiter import limiter

router = APIRouter()

def user_token_key(request: Request) -> str:
    fallback_ip = request.client.host if request.client else "127.0.0.1"
    return request.headers.get("Authorization", fallback_ip)

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute", key_func=user_token_key)
def create_product(
    request: Request,
    product_in: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a product. Enforces Free Tier limits using cross-schema raw SQL.
    """
    tenant_record = db.execute(
        text("SELECT stripe_subscription_id FROM public.tenants WHERE id = :tid"),
        {"tid": str(current_user.tenant_id)}
    ).fetchone()
    
    is_free_tier = tenant_record is None or tenant_record[0] is None
    
    active_products_count = db.query(Product).filter(
        Product.tenant_id == current_user.tenant_id,
        Product.deleted_at == None
    ).count()

    free_limit = 5

    if is_free_tier and active_products_count >= free_limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Product limit reached for Free Tier. Please upgrade to the Pro plan (US$ 99/month)."
        )

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

@router.post("/bulk", response_model=List[ProductResponse], status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute", key_func=user_token_key)
def bulk_create_products(
    request: Request,
    products_in: List[ProductCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Processes batch insertion of products while enforcing tier limits.
    """
    tenant_record = db.execute(
        text("SELECT stripe_subscription_id FROM public.tenants WHERE id = :tid"),
        {"tid": str(current_user.tenant_id)}
    ).fetchone()
    
    is_free_tier = tenant_record is None or tenant_record[0] is None
    
    active_products_count = db.query(Product).filter(
        Product.tenant_id == current_user.tenant_id,
        Product.deleted_at == None
    ).count()

    free_limit = 5

    if is_free_tier and (active_products_count + len(products_in)) > free_limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Bulk insert rejected. This batch would exceed your Free Tier limit of {free_limit} products."
        )

    created_products = ProductService.bulk_create(
        db=db,
        products_in=products_in,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id
    )

    if not created_products:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bulk insertion failed. One or more products caused a SKU conflict. The entire batch was rolled back."
        )

    return created_products

@router.get("/", response_model=PaginatedResponse[ProductResponse])
@limiter.limit("120/minute", key_func=user_token_key)
def list_products(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    name: str | None = Query(None, description="Filter by product name"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ProductService.get_paginated_products(
        db=db,
        tenant_id=current_user.tenant_id,
        page=page,
        size=size,
        name_filter=name
    )

@router.post("/{product_id}/image", response_model=ProductResponse)
@limiter.limit("30/minute", key_func=user_token_key)
async def upload_product_image(
    request: Request,
    product_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("60/minute", key_func=user_token_key)
def delete_product(
    request: Request,
    product_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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