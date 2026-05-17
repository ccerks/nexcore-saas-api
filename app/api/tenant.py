from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.tenant import TenantCreate, TenantResponse, TenantProvisionResponse
from app.schemas.pagination import PaginatedResponse
from app.services.tenant import TenantService
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/", response_model=TenantProvisionResponse, status_code=status.HTTP_201_CREATED)
def create_tenant(
    tenant_in: TenantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Provisions a new Tenant. Strictly locked to 'superadmin' roles to prevent unauthorized platform scaling.
    Returns the auto-generated master credentials.
    """
    if current_user.role != "superadmin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin privileges required.")

    existing_tenant = TenantService.get_by_slug(db, slug=tenant_in.slug)
    if existing_tenant:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A tenant with this slug already exists.")

    try:
        return TenantService.create(db, tenant_in=tenant_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/", response_model=PaginatedResponse[TenantResponse])
def get_all_tenants(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    name: str = Query(None, description="Partial filter by tenant name"),
    is_active: bool = Query(None, description="Exact filter by active status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Superadmin exclusive endpoint to monitor all global tenants."""
    if current_user.role != "superadmin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin privileges required.")
    
    return TenantService.get_paginated(db, page=page, size=size, name=name, is_active=is_active)

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