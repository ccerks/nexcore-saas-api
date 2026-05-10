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
    current_user: User = Depends(get_current_user) # Require auth
):
    # RBAC Check: Only admins can create new tenants
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403, 
            detail="The user does not have enough privileges"
        )
        
    from app.services.tenant import TenantService
    if TenantService.get_by_slug(db, slug=tenant.slug):
        raise HTTPException(status_code=400, detail="Tenant slug already registered")
    
    return TenantService.create(db, tenant_in=tenant)

@router.get("/", response_model=List[TenantResponse])
def read_tenants(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    O Filtro de Identidade:
    Aqui decidimos o que o Treinador pode ver baseado no Crachá (Role).
    """
    # Se for o "Professor Carvalho" (Admin), ele tem visão global de todos os Ginásios.
    if current_user.role == "admin":
        return db.query(Tenant).all()
    
    # Se for um Treinador comum (user), o GPS dele é travado.
    # Ele só consegue listar o Ginásio (Tenant) ao qual ele pertence.
    # Isso impede que o usuário do 'Tenant A' veja dados do 'Tenant B'.
    return db.query(Tenant).filter(Tenant.id == current_user.tenant_id).all()