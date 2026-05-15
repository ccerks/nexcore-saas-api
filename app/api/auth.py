from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.limiter import limiter
from app.db.session import get_db
from app.services.user import UserService
from app.core.security import create_access_token
from app.schemas.token import Token

router = APIRouter()

@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(
    request: Request,  
    db: Session = Depends(get_db), 
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Authenticates a user and returns a JWT access token.
    Protected by Rate Limiting (Maximum of 5 attempts per minute per IP).
    """
    user = UserService.authenticate(db, email=form_data.username, password=form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}