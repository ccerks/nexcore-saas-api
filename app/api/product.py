from fastapi import APIRouter, Depends, HTTPException, Query, status, File, UploadFile, Response, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from uuid import UUID
from typing import List

from app.api.deps import get_current_user, get_tenant_db
from app.models.user import User
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.schemas.pagination import PaginatedResponse
from app.services.product import ProductService
from app.services.storage import StorageService
from app.core.limiter import limiter

router = APIRouter()

def user_token_key(request: Request) -> str:
    fallback_ip = request.client.host if request.client else "127.0.0.1"
    return request.headers.get("Authorization", fallback_ip)

def ensure_tenant_context(user: User):
    """Architectural Shield: Prevents global Superadmins from executing tenant-bound queries without Impersonation."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context required. Superadmins must provide x-tenant-id header."
        )

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute", key_func=user_token_key)
def create_product(
    request: Request,
    product_in: ProductCreate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Creates a product. Enforces Free Tier limits using cross-schema raw SQL."""
    ensure_tenant_context(current_user)

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
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Processes batch insertion of products while enforcing tier limits."""
    ensure_tenant_context(current_user)

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

@router.patch("/{product_id}", response_model=ProductResponse)
@limiter.limit("60/minute", key_func=user_token_key)
def update_product(
    request: Request,
    product_id: UUID,
    product_in: ProductUpdate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """
    Applies partial modifications to a product. 
    Enforces tenant context isolation and automatically tracks the actor.
    """
    ensure_tenant_context(current_user)
    
    update_data = product_in.model_dump(exclude_unset=True)
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="No valid fields provided for update."
        )

    product = ProductService.update(
        db=db,
        product_id=product_id,
        product_in=update_data,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id
    )
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or soft-deleted."
        )
        
    return product

@router.get("/", response_model=PaginatedResponse[ProductResponse])
@limiter.limit("120/minute", key_func=user_token_key)
def list_products(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    name: str | None = Query(None, description="Filter by product name"),
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves paginated catalog items dynamically filtered by tenant."""
    ensure_tenant_context(current_user)
    return ProductService.get_paginated_products(
        db=db,
        tenant_id=current_user.tenant_id,
        page=page,
        size=size,
        name_filter=name
    )

@router.post("/{product_id}/images", response_model=ProductResponse)
@limiter.limit("30/minute", key_func=user_token_key)
async def upload_product_images(
    request: Request,
    product_id: UUID,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """
    Handles bulk image uploads via Multipart Form-Data.
    Streams files to the storage provider and records metadata within a single atomic transaction.
    """
    ensure_tenant_context(current_user)
    
    product = db.query(Product).filter(
        Product.id == product_id, 
        Product.tenant_id == current_user.tenant_id, 
        Product.deleted_at == None
    ).first()
    
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")

    for file in files:
        image_url = await StorageService.save_product_image(file, str(current_user.tenant_id), str(product_id))
        ProductService.add_image_record(db, product_id, current_user.tenant_id, image_url, file.filename)
        
    db.commit()
    db.refresh(product)
    
    return product

@router.patch("/{product_id}/images/{image_id}/main", response_model=ProductResponse)
@limiter.limit("30/minute", key_func=user_token_key)
def set_main_product_image(
    request: Request,
    product_id: UUID,
    image_id: UUID,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Sets a specific image as the primary storefront thumbnail."""
    ensure_tenant_context(current_user)
    
    success = ProductService.set_main_image(
        db=db,
        product_id=product_id,
        image_id=image_id,
        tenant_id=current_user.tenant_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product or Image not found."
        )
        
    product = db.query(Product).filter(
        Product.id == product_id, 
        Product.tenant_id == current_user.tenant_id
    ).first()
    
    return product

@router.delete("/{product_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("60/minute", key_func=user_token_key)
def delete_product_image(
    request: Request,
    product_id: UUID,
    image_id: UUID,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Deletes a specific product image. Triggers asynchronous storage cleanup."""
    ensure_tenant_context(current_user)
    
    success = ProductService.delete_image_record(
        db=db,
        product_id=product_id,
        image_id=image_id,
        tenant_id=current_user.tenant_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image or Product not found."
        )
        
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("60/minute", key_func=user_token_key)
def delete_product(
    request: Request,
    product_id: UUID,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Soft deletes a product."""
    ensure_tenant_context(current_user)
    success = ProductService.delete(
        db=db,
        product_id=product_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id
    )
    
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or already deleted.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.patch("/{product_id}/restore", response_model=ProductResponse)
@limiter.limit("30/minute", key_func=user_token_key)
def restore_product(
    request: Request,
    product_id: UUID,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Restores a previously soft-deleted product."""
    ensure_tenant_context(current_user)

    product = ProductService.restore(
        db=db,
        product_id=product_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id
    )

    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or already active.")

    return product