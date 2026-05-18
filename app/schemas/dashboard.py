from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime
from uuid import UUID

class ProductSummary(BaseModel):
    """
    Lightweight DTO for public marketplace or dashboard aggregation screens.
    Architectural Fix: Replaced Portuguese 'sku_pai' with unified clean English asset property.
    """
    id: UUID
    name: str
    sku: str
    price: float
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class AuditLogSummary(BaseModel):
    id: UUID
    action: str
    entity_name: str
    entity_id: str
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class DashboardMetricsResponse(BaseModel):
    """
    Aggregates all multi-tenant metrics into a single high-performance payload.
    Implements the Backend-For-Frontend (BFF) structural design pattern.
    """
    total_active_products: int
    total_deleted_products: int
    total_without_images: int
    total_with_variations: int
    recently_added: List[ProductSummary]
    recent_changes: List[AuditLogSummary]