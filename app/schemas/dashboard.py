from pydantic import BaseModel
from typing import List
from app.schemas.audit import AuditLogResponse

class DashboardSummary(BaseModel):
    total_active_products: int
    out_of_stock_products: int
    recent_activity: List[AuditLogResponse]