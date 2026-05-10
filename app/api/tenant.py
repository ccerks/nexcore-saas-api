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
def create_tenant(tenant: TenantCreate, db: Session = Depends(get_db)):
    # 1. Check constraints using the Service layer
    if TenantService.get_by_slug(db, slug=tenant.slug):
        raise HTTPException(status_code=400, detail="Tenant slug already registered")
    
    # 2. Delegate creation to the Service layer
    return TenantService.create(db, tenant_in=tenant)

@router.get("/", response_model=List[TenantResponse])
def read_tenants(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # The lock is here!
):
    """Retrieve all tenants. Requires authentication."""
    return db.query(Tenant).all()