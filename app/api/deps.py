import logging
import jwt
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, Generator
from uuid import UUID

from app.db.session import get_db
from app.core.config import settings
from app.services.user import UserService
from app.models.user import User
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    x_tenant_id: Optional[UUID] = Header(
        None,
        description="Superadmin impersonation header. Injects an ephemeral tenant context.",
    ),
) -> User:
    """
    Validates the JWT and resolves the caller's identity.

    Superadmin impersonation: when x_tenant_id is supplied by a superadmin,
    the user object receives an ephemeral tenant_id so downstream handlers
    behave identically to a regular tenant-scoped request.
    Every impersonation session is written to the application security log.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or token expired.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    db.execute(text('SET search_path TO "public"'))

    user = UserService.get_by_email(db, email=email)
    if user is None or not user.is_active:
        raise credentials_exception

    if user.role == "superadmin":
        if x_tenant_id:
            tenant = db.get(Tenant, x_tenant_id)
            if not tenant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Target tenant for impersonation not found.",
                )

            # Security audit trail: every impersonation session must be traceable.
            logger.warning(
                "SUPERADMIN_IMPERSONATION | actor=%s | target_tenant=%s | target_tenant_id=%s",
                user.email,
                tenant.slug,
                x_tenant_id,
            )

            # Ephemeral tenant injection: expunge the user from the session to allow
            # mutating tenant_id without persisting the change to the database.
            db.expunge(user)
            user.tenant_id = tenant.id

        return user

    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User lacks tenant association.",
        )

    tenant = db.get(Tenant, user.tenant_id)
    if not tenant or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant account is inactive or suspended.",
        )

    return user


def get_tenant_db(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Generator[Session, None, None]:
    """
    Context-aware session router.

    Sets the PostgreSQL search_path to the tenant's dedicated schema before
    yielding the session, and reverts it to 'public' in the finally block
    to prevent connection-pool poisoning across requests.
    """
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active tenant isolation context could not be verified.",
        )

    tenant = db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant context not found.",
        )

    schema_name = f"tenant_{tenant.slug}"
    db.execute(text(f'SET search_path TO "{schema_name}", "public"'))

    try:
        yield db
    finally:
        db.execute(text('SET search_path TO "public"'))
