from pydantic import BaseModel, ConfigDict, field_validator, Field
from uuid import UUID, uuid4
from typing import Optional, Dict, Any, Union

class ProductBase(BaseModel):
    name: str = Field(
        ..., 
        description="The commercial name of the product.", 
        examples=["Wireless Bluetooth Headphones"]
    )
    description: str | None = Field(
        None, 
        description="Detailed text or HTML description of the product.", 
        examples=["High-fidelity noise-canceling headphones with a 30-hour battery life."]
    )
    sku_pai: str = Field(
        ..., 
        description="The master Stock Keeping Unit (SKU) identifying the base product family.", 
        examples=["WH-1000XM4"]
    )
    sku_filho: str | None = Field(
        None, 
        description="The specific variation SKU (e.g., color or size dimension).", 
        examples=["WH-1000XM4-BLK"]
    )
    ean: str | None = Field(
        None, 
        description="European Article Number (EAN) or commercial barcode.", 
        examples=["4548736112100"]
    )
    is_variation: bool = Field(
        False, 
        description="Flag indicating if this record represents a variation of a master product.", 
        examples=[False]
    )
    price: float = Field(
        ..., 
        description="The current retail price of the product.", 
        examples=[349.99]
    )
    stock: int = Field(
        0, 
        description="Available inventory count.", 
        examples=[150]
    )
    attributes: Dict[str, Any] | None = Field(
        None, 
        description="Dynamic JSON attributes for custom product specifications.", 
        examples=[{"color": "Black", "weight": "254g"}]
    )
    image_url: str | None = Field(
        None, 
        description="The absolute or relative URL to the product's primary image.", 
        examples=["/static/products/123e4567-e89b-12d3/headphone-blk.jpg"]
    )

class ProductCreate(ProductBase):
    id: Optional[UUID] = Field(default_factory=uuid4, description="Optional UUID assignment for hierarchical bulk inserts.")
    parent_id: Optional[UUID] = Field(None, description="The UUID of the master product if this is a variation.")
    attributes: Optional[Union[str, Dict[str, Any]]] = Field(None, examples=['color:Black, weight:254g'])

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
                
                if ':' not in pair:
                    raise ValueError(f"Invalid attribute format: '{pair}'. Expected pattern is 'key:value'.")
                
                key, value = pair.split(':', 1)
                parsed_dict[key.strip()] = value.strip()
                
            return parsed_dict
            
        return v

class ProductResponse(ProductBase):
    id: UUID = Field(..., description="The unique identifier for the product.")
    tenant_id: UUID = Field(..., description="The dimension ID restricting this product to its owner.")
    parent_id: Optional[UUID] = Field(None)
    deactivation_count: int = Field(0, description="Counter tracking how many times the product was soft-deleted.")
    
    @field_validator('deactivation_count', mode='before')
    @classmethod
    def set_legacy_deactivation_count(cls, v: Any) -> int:
        return v if v is not None else 0
    
    model_config = ConfigDict(from_attributes=True)