from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime
from uuid import UUID

class ProductSummary(BaseModel):
    id: UUID
    name: str
    sku_pai: str
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
    Aggregates all metrics into a single JSON payload.
    Implements the Backend-For-Frontend (BFF) pattern.
    """
    total_active_products: int
    total_deleted_products: int
    total_without_images: int
    total_with_variations: int
    recently_added: List[ProductSummary]
    recent_changes: List[AuditLogSummary]