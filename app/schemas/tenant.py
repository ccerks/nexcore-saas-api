from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime

class TenantCreate(BaseModel):
    name: str
    slug: str

class TenantResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    is_active: bool
    created_at: datetime

    # Tells Pydantic to read data even if it is not a dict (like a SQLAlchemy model)
    model_config = ConfigDict(from_attributes=True)