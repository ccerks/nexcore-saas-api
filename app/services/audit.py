import math
from sqlalchemy.orm import Session
from typing import Any, Dict, List
from uuid import UUID

from app.models.audit import AuditLog

class AuditService:
    
    @staticmethod
    def log_action(
        db: Session,
        tenant_id: UUID,
        user_id: UUID | None,
        action: str,
        entity_name: str,
        entity_id: str,
        changes: Dict[str, Any] | None = None
    ) -> None:
        """
        Records an action in the system's audit log.
        This method operates on the existing database session but does not commit,
        allowing it to be part of an atomic transaction.
        """
        audit_entry = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action.upper(),
            entity_name=entity_name,
            entity_id=entity_id,
            changes=changes
        )
        
        db.add(audit_entry)
        # Note: The commit is handled by the caller to ensure this log entry is part of the same transaction.

    @staticmethod
    def get_paginated_logs(
        db: Session, 
        tenant_id: UUID, 
        page: int = 1, 
        size: int = 20
    ) -> dict:
        query = db.query(AuditLog).filter(AuditLog.tenant_id == tenant_id).order_by(AuditLog.created_at.desc())

        total_records = query.count()
        total_pages = math.ceil(total_records / size) if total_records > 0 else 1
        
        offset_value = (page - 1) * size
        logs = query.offset(offset_value).limit(size).all()

        return {
            "items": logs,
            "total": total_records,
            "page": page,
            "size": size,
            "pages": total_pages
        }        