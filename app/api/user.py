from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.user import UserCreate, UserResponse
from app.services.user import UserService
from app.api.deps import get_current_user
from app.models.user import User
from app.core.limiter import limiter

router = APIRouter()

@router.post("/", response_model=UserResponse, status_code=201)
@limiter.limit("5/minute")
def create_user(
    request: Request, 
    user: UserCreate, 
    db: Session = Depends(get_db)
):
    if UserService.get_by_email(db, email=user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    return UserService.create(db, user_in=user)

@router.get("/me", response_model=UserResponse)
def read_user_me(current_user: User = Depends(get_current_user)):
    """
    Get current logged in user information.
    """
    return current_user