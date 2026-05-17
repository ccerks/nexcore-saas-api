import jwt
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from uuid import UUID

from app.db.session import get_db
from app.core.config import settings
from app.services.user import UserService
from app.models.user import User
from app.models.tenant import Tenant

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db),
    x_tenant_id: Optional[UUID] = Header(None, description="Superadmin context switcher (Impersonation)")
) -> User:
    """
    Validates identity and dynamically binds the SQLAlchemy Session 
    to the isolated PostgreSQL schema. Implements secure JWT decoding order
    and Superadmin impersonation capabilities.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or token expired.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 1. Strict Token Decoding Order (Resolves UnboundLocalError)
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
        
    # Force context to public to validate global credentials safely
    db.execute(text('SET search_path TO "public"'))
        
    # 2. Identity Resolution
    user = UserService.get_by_email(db, email=email)
    if user is None or not user.is_active:
        raise credentials_exception

    # 3. Superadmin Context Switching (Arceus Plate mechanic)
    if user.role == "superadmin":
        if x_tenant_id:
            tenant = db.query(Tenant).get(x_tenant_id)
            if not tenant:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target tenant for impersonation not found.")
            
            schema_name = f"tenant_{tenant.slug}"
            db.execute(text(f'SET search_path TO "{schema_name}", "public"'))
            
            # Architectural Magic: Ephemeral DNA injection
            # Fools downstream endpoints into believing the Superadmin organically belongs to the target tenant
            db.expunge(user)
            user.tenant_id = tenant.id
        else:
            db.execute(text('SET search_path TO "public"'))
            
        return user

    # 4. Standard Tenant Access Shield
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User lacks tenant association.")

    tenant = db.query(Tenant).get(user.tenant_id)
    if not tenant or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Tenant account is inactive or suspended."
        )

    # Architectural Fix: Inline search_path configuration without db.commit()
    schema_name = f"tenant_{tenant.slug}"
    db.execute(text(f'SET search_path TO "{schema_name}", "public"'))

    return user