from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.dashboard import DashboardMetricsResponse
from app.services.dashboard import DashboardService
from app.core.limiter import limiter

router = APIRouter()

def user_token_key(request: Request) -> str:
    fallback_ip = request.client.host if request.client else "127.0.0.1"
    return request.headers.get("Authorization", fallback_ip)

@router.get("/summary", response_model=DashboardMetricsResponse)
@limiter.limit("30/minute", key_func=user_token_key)
def get_dashboard_summary(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve aggregated metrics and recent activity for the tenant's dashboard.
    Implements rate limiting to prevent heavy aggregate query abuse.
    """
    return DashboardService.get_summary(db=db, tenant_id=current_user.tenant_id)