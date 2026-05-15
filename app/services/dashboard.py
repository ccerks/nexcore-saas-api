from sqlalchemy.orm import Session
from uuid import UUID

from app.models.product import Product
from app.models.audit import AuditLog

class DashboardService:
    """
    Handles data aggregation for the BFF layer.
    Architectural Note: Relies on PostgreSQL's physical schema isolation (search_path).
    Explicit tenant_id filtering is omitted as the session is already confined to the tenant's dimension.
    """
    
    @staticmethod
    def get_summary(db: Session) -> dict:
        """
        Aggregates key metrics for the tenant's executive dashboard.
        Executes highly optimized COUNT queries within the isolated schema.
        """
        active_count = db.query(Product).filter(
            Product.deleted_at.is_(None)
        ).count()
        
        deleted_count = db.query(Product).filter(
            Product.deleted_at.is_not(None)
        ).count()
        
        no_image_count = db.query(Product).filter(
            Product.image_url.is_(None),
            Product.deleted_at.is_(None)
        ).count()
        
        variations_count = db.query(Product).filter(
            Product.parent_id.is_not(None),
            Product.deleted_at.is_(None)
        ).count()
        
        recent_products = db.query(Product).filter(
            Product.deleted_at.is_(None)
        ).order_by(Product.id.desc()).limit(5).all()
        
        recent_logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(5).all()

        return {
            "total_active_products": active_count,
            "total_deleted_products": deleted_count,
            "total_without_images": no_image_count,
            "total_with_variations": variations_count,
            "recently_added": recent_products,
            "recent_changes": recent_logs
        }