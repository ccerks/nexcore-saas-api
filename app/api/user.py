from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from app.schemas.user import UserCreate, UserResponse
from app.services.user import UserService
from app.api.deps import get_current_user
from app.models.user import User
from app.core.limiter import limiter

router = APIRouter()

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def create_user(
    request: Request, 
    user_in: UserCreate, 
    db: Session = Depends(get_db)
):
    """
    Creates a new user. Enforces 'public' schema context to ensure 
    global table consistency and valid foreign key referencing.
    """
    # Architectural Safety: Force context to 'public' for global user provisioning
    db.execute(text('SET search_path TO "public"'))
    
    if UserService.get_by_email(db, email=user_in.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email already registered"
        )
    
    try:
        return UserService.create(db, user_in=user_in)
    except Exception:
        # Handles cases like the one encountered in Swagger (invalid tenant_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant_id. The referenced tenant does not exist in the public record."
        )

@router.get("/me", response_model=UserResponse)
def read_user_me(current_user: User = Depends(get_current_user)):
    return current_user