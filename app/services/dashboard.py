from sqlalchemy.orm import Session
from uuid import UUID

from app.models.product import Product
from app.models.audit import AuditLog

class DashboardService:
    
    @staticmethod
    def get_summary(db: Session, tenant_id: UUID) -> dict:
        """
        Aggregates key metrics for the tenant's executive dashboard.
        Executes highly optimized COUNT queries.
        """
        active_count = db.query(Product).filter(
            Product.tenant_id == tenant_id,
            Product.deleted_at == None
        ).count()
        
        deleted_count = db.query(Product).filter(
            Product.tenant_id == tenant_id,
            Product.deleted_at != None
        ).count()
        
        no_image_count = db.query(Product).filter(
            Product.tenant_id == tenant_id,
            Product.image_url == None,
            Product.deleted_at == None
        ).count()
        
        variations_count = db.query(Product).filter(
            Product.tenant_id == tenant_id,
            Product.parent_id != None,
            Product.deleted_at == None
        ).count()
        
        recent_products = db.query(Product).filter(
            Product.tenant_id == tenant_id,
            Product.deleted_at == None
        ).order_by(Product.id.desc()).limit(5).all()
        
        recent_logs = db.query(AuditLog).filter(
            AuditLog.tenant_id == tenant_id
        ).order_by(AuditLog.created_at.desc()).limit(5).all()

        return {
            "total_active_products": active_count,
            "total_deleted_products": deleted_count,
            "total_without_images": no_image_count,
            "total_with_variations": variations_count,
            "recently_added": recent_products,
            "recent_changes": recent_logs
        }