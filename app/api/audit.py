from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.audit import AuditLogResponse
from app.schemas.pagination import PaginatedResponse
from app.services.audit import AuditService

router = APIRouter()

@router.get("/", response_model=PaginatedResponse[AuditLogResponse])
def list_audit_logs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve audit logs for the authenticated tenant.
    Ordered by most recent first.
    """
    return AuditService.get_paginated_logs(
        db=db,
        tenant_id=current_user.tenant_id,
        page=page,
        size=size
    )