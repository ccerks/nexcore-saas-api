from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime

class TenantCreate(BaseModel):
    name: str = Field(
        ..., 
        description="The official legal name or trading name of the tenant's business.",
        examples=["Acme Corporation"]
    )
    slug: str = Field(
        ..., 
        description="A unique, URL-friendly identifier for the tenant's workspace.",
        examples=["acme-corp"]
    )

class TenantResponse(BaseModel):
    id: UUID = Field(..., description="The unique physical dimension ID of the tenant.")
    name: str = Field(..., examples=["Acme Corporation"])
    slug: str = Field(..., examples=["acme-corp"])
    is_active: bool = Field(..., description="Indicates if the tenant has access to the platform based on billing status.")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)