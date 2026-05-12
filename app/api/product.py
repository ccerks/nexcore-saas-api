from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.product import ProductCreate, ProductResponse
from app.schemas.pagination import PaginatedResponse
from app.services.product import ProductService

router = APIRouter()

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product_in: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new product for the authenticated tenant.
    Validates SKU uniqueness to prevent duplicates.
    """
    existing_product = ProductService.get_by_sku(
        db=db, 
        tenant_id=current_user.tenant_id, 
        sku_pai=product_in.sku_pai, 
        sku_filho=product_in.sku_filho
    )
    
    if existing_product:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A product with this SKU already exists in your catalog."
        )

    return ProductService.create(
        db=db, 
        product_in=product_in, 
        tenant_id=current_user.tenant_id
    )


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