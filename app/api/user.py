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

@router.post("/employee", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def create_employee(
    request: Request, 
    user_in: UserCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a new user strictly bound to the authenticated admin's tenant.
    Prevents cross-tenant injection by overriding the payload's tenant_id.
    """
    db.execute(text('SET search_path TO "public"'))
    
    # Architectural Shield: Enforce tenant isolation regardless of payload
    user_in.tenant_id = current_user.tenant_id
    
    if UserService.get_by_email(db, email=user_in.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email already registered in the system."
        )
    
    return UserService.create(db, user_in=user_in)

@router.get("/me", response_model=UserResponse)
def read_user_me(current_user: User = Depends(get_current_user)):
    return current_user