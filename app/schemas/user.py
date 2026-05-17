from pydantic import BaseModel, ConfigDict, field_validator, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Literal

def validate_strong_password(v: str) -> str:
    if len(v) < 8:
        raise ValueError('Password must be at least 8 characters long')
    if not any(char.isdigit() for char in v):
        raise ValueError('Password must contain at least one digit')
    if not any(char.isupper() or not char.isalnum() for char in v):
        raise ValueError('Password must contain at least one uppercase letter or symbol')
    return v

class UserCreate(BaseModel):
    tenant_id: Optional[UUID] = Field(None, description="Bound tenant ID.")
    # Architectural Fix: Mandatory friendly identifier
    username: str = Field(..., description="Unique alphanumeric identifier (no spaces).", examples=["ashketchum"])
    email: str = Field(..., examples=["employee@acme-corp.com"])
    password: str = Field(..., description="Must contain 8+ chars, 1 digit, 1 uppercase/symbol.")
    full_name: Optional[str] = Field(None, examples=["John Doe"])
    role: Literal["superadmin", "admin", "user"] = Field(
        default="user", 
        description="RBAC role defining access level."
    )

    @field_validator('password')
    @classmethod
    def validate_password_creation(cls, v: str) -> str:
        return validate_strong_password(v)

class UserUpdatePassword(BaseModel):
    """DTO strictly dedicated to secure password rotation."""
    current_password: str = Field(..., description="Required to verify current identity.")
    new_password: str = Field(..., description="The new strong password.")

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return validate_strong_password(v)

class UserUpdateRole(BaseModel):
    """DTO strictly dedicated to RBAC privilege escalation/de-escalation."""
    role: Literal["superadmin", "admin", "user"] = Field(..., description="The new target role.")

class UserResponse(BaseModel):
    id: UUID = Field(...)
    tenant_id: Optional[UUID] = Field(None)
    # Architectural Fix: Return friendly identifier in responses
    username: str = Field(...)
    email: str = Field(...)
    full_name: Optional[str] = Field(None)
    role: str = Field(...)
    is_active: bool = Field(..., description="Operational status. False indicates a soft-deleted or suspended user.")
    created_at: datetime = Field(...)

    model_config = ConfigDict(from_attributes=True)