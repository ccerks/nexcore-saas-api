from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.tenant import TenantCreate, TenantResponse
from app.services.tenant import TenantService

router = APIRouter()

@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
def create_tenant(
    tenant_in: TenantCreate,
    db: Session = Depends(get_db)
):
    """
    Creates a new Tenant.
    Automatically provisions Stripe billing and a Dedicated Database Schema.
    """
    existing_tenant = TenantService.get_by_slug(db, slug=tenant_in.slug)
    if existing_tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A tenant with this slug already exists."
        )

    try:
        tenant = TenantService.create(db, tenant_in=tenant_in)
        return tenant
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{tenant_id}", response_model=TenantResponse)
def get_tenant(
    tenant_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves a specific tenant by ID.
    """
    tenant = TenantService.get(db, tenant_id=tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found."
        )
    return tenant