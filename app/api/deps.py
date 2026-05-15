import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_db
from app.core.config import settings
from app.services.user import UserService
from app.models.user import User
from app.models.tenant import Tenant

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    """
    Validates identity and dynamically binds the SQLAlchemy Session 
    to the tenant's isolated PostgreSQL schema without committing, 
    preserving the context for subsequent transactional queries.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    # Force context to public to validate global credentials safely
    db.execute(text('SET search_path TO "public"'))
        
    user = UserService.get_by_email(db, email=email)
    if user is None or not user.is_active:
        raise credentials_exception

    tenant = db.query(Tenant).get(user.tenant_id)
    if not tenant or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Tenant account is inactive or suspended."
        )

    # Architectural Fix: Inline search_path configuration.
    # Omitting db.commit() ensures the transaction remains open and 
    # the Connection Pool does not reset the path to 'public'.
    schema_name = f"tenant_{tenant.slug}"
    db.execute(text(f'SET search_path TO "{schema_name}", "public"'))

    return user