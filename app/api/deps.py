import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.session import get_db, set_tenant_schema
from app.core.config import settings
from app.services.user import UserService
from app.models.user import User
from app.models.tenant import Tenant

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    """
    Decodes the JWT token, returns the authenticated user, and dynamically
    routes the database session to the user's dedicated physical schema.
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
        
    user = UserService.get_by_email(db, email=email)
    if user is None or not user.is_active:
        raise credentials_exception

    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if not tenant or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Tenant account is inactive or suspended."
        )

    # Enterprise Isolation: Switch DB context to the dedicated schema
    set_tenant_schema(db=db, tenant_slug=tenant.slug)

    return user