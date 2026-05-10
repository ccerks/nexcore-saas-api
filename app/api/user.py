from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.user import UserCreate, UserResponse
from app.services.user import UserService

router = APIRouter()

@router.post("/", response_model=UserResponse, status_code=201)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    # 1. Check if email is already registered
    if UserService.get_by_email(db, email=user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # 2. Note: Tenant validation could be added here to ensure the tenant_id exists
    
    # 3. Delegate user creation and password hashing to the Service layer
    return UserService.create(db, user_in=user)