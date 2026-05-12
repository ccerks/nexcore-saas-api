from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Any, Dict

class AuditLogResponse(BaseModel):
    id: UUID
    user_id: UUID | None
    action: str
    entity_name: str
    entity_id: str
    changes: Dict[str, Any] | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)