from pydantic import BaseModel, ConfigDict, field_validator
from uuid import UUID
from typing import Optional, Dict, Any, Union

class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    sku_pai: str
    sku_filho: Optional[str] = None
    ean: Optional[str] = None
    is_variation: bool = False
    price: float
    stock: int = 0

class ProductCreate(ProductBase):
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
    attributes: Optional[Dict[str, Any]] = None 

    model_config = ConfigDict(from_attributes=True)