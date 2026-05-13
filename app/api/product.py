from fastapi import APIRouter, Depends, HTTPException, Query, status, File, UploadFile, Response, Request
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.product import Product
from app.models.tenant import Tenant
from app.schemas.product import ProductCreate, ProductResponse
from app.schemas.pagination import PaginatedResponse
from app.services.product import ProductService
from app.services.storage import StorageService
from app.core.limiter import limiter

router = APIRouter()

def user_token_key(request: Request) -> str:
    """
    Custom key function for SlowAPI.
    Uses the Authorization token as the rate limit key instead of the IP address.
    This ensures that limits are applied per authenticated tenant session,
    preventing the 'Noisy Neighbor' problem in shared IP environments.
    """
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
    Creates a single new product. 
    Enforces free tier limits, handles SKU conflicts, and limits creation rate per tenant.
    """
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    
    active_products_count = db.query(Product).filter(
        Product.tenant_id == current_user.tenant_id,
        Product.deleted_at == None
    ).count()

    is_free_tier = not tenant.stripe_subscription_id
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
    Creates multiple products in a single transaction (Bulk Insert).
    Enforces quota limits based on the total batch size to prevent limit circumvention.
    """
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    
    active_products_count = db.query(Product).filter(
        Product.tenant_id == current_user.tenant_id,
        Product.deleted_at == None
    ).count()

    is_free_tier = not tenant.stripe_subscription_id
    free_limit = 5

    if is_free_tier and (active_products_count + len(products_in)) > free_limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Bulk insert rejected. This batch would exceed your Free Tier limit of {free_limit} products. You currently have {active_products_count} active products."
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
    """
    Retrieves a paginated list of products for the authenticated tenant.
    Allows a higher request rate for read-only operations.
    """
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
    """
    Uploads a main image for a specific product securely.
    Strictly rate-limited due to I/O and storage constraints.
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

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("60/minute", key_func=user_token_key)
def delete_product(
    request: Request,
    product_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Soft-deletes a product, hiding it from catalogs but retaining it in the database.
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