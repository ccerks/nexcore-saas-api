from pydantic import BaseModel, ConfigDict, field_validator, Field
from uuid import UUID, uuid4
from typing import Optional, Dict, Any, Union

class ProductBase(BaseModel):
    name: str
    description: str | None = None
    sku_pai: str
    sku_filho: str | None = None
    ean: str | None = None
    is_variation: bool = False
    price: float
    stock: int = 0
    attributes: Dict[str, Any] | None = None
    image_url: str | None = None

class ProductCreate(ProductBase):
    # Architectural Fix: Enables client-side ID assignment for hierarchical bulk inserts.
    # Generates a secure UUIDv4 automatically if not provided in the payload.
    id: Optional[UUID] = Field(default_factory=uuid4)
    parent_id: Optional[UUID] = None
    attributes: Optional[Union[str, Dict[str, Any]]] = None

    @field_validator('attributes', mode='before')
    @classmethod
    def parse_attributes_string(cls, v: Any) -> Optional[Dict[str, str]]:
        if not v:
            return None
        if isinstance(v, dict):
            return v
        
        if isinstance(v, str):
            parsed_dict = {}
            pairs = v.split(',')
            for pair in pairs:
                pair = pair.strip()
                if not pair:
                    continue
                
                # Fail-Fast: Reject invalid formats immediately
                if ':' not in pair:
                    raise ValueError(f"Invalid attribute format: '{pair}'. Expected pattern is 'key:value'.")
                
                key, value = pair.split(':', 1)
                parsed_dict[key.strip()] = value.strip()
                
            return parsed_dict
            
        return v

class ProductResponse(ProductBase):
    id: UUID
    tenant_id: UUID
    parent_id: Optional[UUID] = None
    deactivation_count: int = 0
    
    @field_validator('deactivation_count', mode='before')
    @classmethod
    def set_legacy_deactivation_count(cls, v: Any) -> int:
        """
        Defensive programming for legacy records.
        Converts NULL values from the database into 0.
        """
        return v if v is not None else 0
    
    model_config = ConfigDict(from_attributes=True)