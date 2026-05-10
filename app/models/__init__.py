# Aggregate all models here to ensure they are registered by SQLAlchemy at startup
from app.db.session import Base
from app.models.tenant import Tenant
from app.models.user import User
from .product import Product