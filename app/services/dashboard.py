from sqlalchemy.orm import Session
from uuid import UUID

from app.models.product import Product
from app.models.audit import AuditLog

class DashboardService:
    
    @staticmethod
    def get_summary(db: Session, tenant_id: UUID) -> dict:
        """
        Aggregates key metrics for the tenant's initial dashboard.
        """
        active_products_count = db.query(Product).filter(
            Product.tenant_id == tenant_id,
            Product.deleted_at == None
        ).count()
        
        out_of_stock_count = db.query(Product).filter(
            Product.tenant_id == tenant_id,
            Product.deleted_at == None,
            Product.stock <= 0
        ).count()
        
        recent_logs = db.query(AuditLog).filter(
            AuditLog.tenant_id == tenant_id
        ).order_by(AuditLog.created_at.desc()).limit(5).all()
        
        return {
            "total_active_products": active_products_count,
            "out_of_stock_products": out_of_stock_count,
            "recent_activity": recent_logs
        }