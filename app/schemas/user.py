import re
from pydantic import BaseModel, ConfigDict, field_validator, Field
from uuid import UUID
from datetime import datetime
from typing import Optional

class UserCreate(BaseModel):
    tenant_id: Optional[UUID] = Field(
        None, 
        description="Optional ID to bind the user to a specific tenant. Secure routes will automatically override this.", 
        examples=["123e4567-e89b-12d3-a456-426614174000"]
    )
    email: str = Field(
        ..., 
        description="The corporate or personal email address used for authentication.", 
        examples=["employee@acme-corp.com"]
    )
    password: str = Field(
        ..., 
        description="A strong password containing at least 8 characters, one digit, and one uppercase letter or symbol.", 
        examples=["EnterpriseP@ssw0rd123"]
    )
    full_name: Optional[str] = Field(
        None, 
        description="The user's full legal or preferred name.", 
        examples=["John Doe"]
    )
    role: Optional[str] = Field(
        "user", 
        description="The RBAC role assigned to the user within the tenant's ecosystem.", 
        examples=["admin"]
    )

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        
        if not any(char.isupper() or not char.isalnum() for char in v):
            raise ValueError('Password must contain at least one uppercase letter or symbol')
        
        return v

class UserResponse(BaseModel):
    id: UUID = Field(..., description="The unique identifier for the user.")
    tenant_id: UUID = Field(..., description="The dimension ID linking this user to their workspace.")
    email: str = Field(..., examples=["employee@acme-corp.com"])
    full_name: Optional[str] = Field(None, examples=["John Doe"])
    role: str = Field(..., examples=["admin"])
    is_active: bool = Field(..., description="Indicates if the user is currently authorized to log in.")
    created_at: datetime = Field(...)

    model_config = ConfigDict(from_attributes=True)