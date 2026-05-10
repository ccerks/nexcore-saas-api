from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.schemas.product import ProductCreate, ProductResponse
from app.services.product import ProductService
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product_in: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new product.
    Enforces SKU uniqueness per tenant and injects the user's tenant_id.
    """
    existing_product = ProductService.get_by_sku(
        db, 
        tenant_id=current_user.tenant_id, 
        sku_pai=product_in.sku_pai,
        sku_filho=product_in.sku_filho
    )
    
    if existing_product:
        raise HTTPException(
            status_code=400,
            detail="A product with this SKU configuration already exists in your catalog."
        )
    
    return ProductService.create(db, product_in=product_in, tenant_id=current_user.tenant_id)

@router.get("/", response_model=List[ProductResponse])
def read_products(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve products.
    Strictly isolated: returns only products belonging to the current user's tenant.
    """
    return ProductService.get_all_by_tenant(
        db, tenant_id=current_user.tenant_id, skip=skip, limit=limit
    )