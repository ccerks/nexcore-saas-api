from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.tenant import TenantCreate, TenantResponse
from app.services.tenant import TenantService

router = APIRouter()

@router.post("/", response_model=TenantResponse, status_code=201)
def create_tenant(tenant: TenantCreate, db: Session = Depends(get_db)):
    # 1. Check constraints using the Service layer
    if TenantService.get_by_slug(db, slug=tenant.slug):
        raise HTTPException(status_code=400, detail="Tenant slug already registered")
    
    # 2. Delegate creation to the Service layer
    return TenantService.create(db, tenant_in=tenant)