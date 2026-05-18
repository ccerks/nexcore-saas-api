from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

class ProductImageResponse(BaseModel):
    """Architectural Fix: Dedicated DTO for the 1:N image relationship."""
    id: UUID
    url: str
    alt_text: Optional[str] = None
    is_main: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ProductBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    sku: str = Field(..., max_length=100, description="Unique Stock Keeping Unit within the tenant.")
    ean: Optional[str] = Field(None, max_length=13)
    is_variation: bool = Field(default=False)
    price: float = Field(..., ge=0.0)
    stock: int = Field(default=0, ge=0)
    attributes: Optional[Dict[str, Any]] = None
    parent_id: Optional[UUID] = Field(None, description="Links to a parent product if this is a variation.")

class ProductCreate(ProductBase):
    """DTO for product creation. Swagger UI examples included."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Wireless Bluetooth Headphones",
                "description": "High-fidelity noise-canceling headphones.",
                "sku": "WH-1000XM4-BLK",
                "ean": "4548736112100",
                "is_variation": False,
                "price": 349.99,
                "stock": 150,
                "attributes": {"color": "Black", "weight": "254g"},
                "parent_id": None
            }
        }
    )

class ProductResponse(ProductBase):
    id: UUID
    friendly_id: int = Field(..., description="Regional Pokédex ID (Auto-incremented integer).")
    tenant_id: UUID
    created_at: datetime
    deleted_at: Optional[datetime] = None
    last_deleted_by: Optional[UUID] = None
    deactivation_count: int
    
    # Architectural Fix: Nested collection mapping for the newly uncoupled image architecture
    images: List[ProductImageResponse] = Field(default_factory=list, description="Collection of associated product media.")

    model_config = ConfigDict(from_attributes=True)