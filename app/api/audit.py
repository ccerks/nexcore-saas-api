from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from uuid import UUID

from app.api.deps import get_current_user, get_tenant_db
from app.models.user import User
from app.schemas.audit import AuditLogResponse
from app.schemas.pagination import PaginatedResponse
from app.services.audit import AuditService

router = APIRouter()

@router.get("/", response_model=PaginatedResponse[AuditLogResponse])
def list_audit_logs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve audit logs for the authenticated tenant.
    Ordered by most recent first.
    Architectural Fix: Uses get_tenant_db to route the query to the tenant's
    dedicated schema where the audit_logs table physically resides.
    """
    return AuditService.get_paginated_logs(
        db=db,
        tenant_id=current_user.tenant_id,
        page=page,
        size=size
    )
