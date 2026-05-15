import re
from pydantic import BaseModel, ConfigDict, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional

class UserCreate(BaseModel):
    tenant_id:  Optional[UUID] = None
    email: str
    password: str
    full_name: Optional[str] = None
    role: Optional[str] = "user"

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        
        # Checks if there is at least one uppercase letter OR one special character
        if not any(char.isupper() or not char.isalnum() for char in v):
            raise ValueError('Password must contain at least one uppercase letter or symbol')
        
        return v

class UserResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)