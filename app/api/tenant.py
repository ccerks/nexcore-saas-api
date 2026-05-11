from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List 

from app.db.session import get_db
from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantResponse
from app.services.tenant import TenantService
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/", response_model=TenantResponse, status_code=201)
def create_tenant(
    tenant: TenantCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a new Tenant.
    Requires Admin privileges.
    """
    # RBAC Check: Only admins can provision new tenants
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403, 
            detail="The user does not have enough privileges"
        )
        
    if TenantService.get_by_slug(db, slug=tenant.slug):
        raise HTTPException(status_code=400, detail="Tenant slug already registered")
    
    return TenantService.create(db, tenant_in=tenant)

@router.get("/", response_model=List[TenantResponse])
def read_tenants(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves a list of Tenants.
    Applies Data Isolation: Admins see all, regular users see only their own.
    """
    # Global visibility for administrators
    if current_user.role == "admin":
        return db.query(Tenant).all()
    
    # Data isolation for standard users
    return db.query(Tenant).filter(Tenant.id == current_user.tenant_id).all()