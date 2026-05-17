import secrets
import string
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from uuid import UUID

from app.db.session import get_db
from app.schemas.user import UserCreate, UserResponse, UserUpdatePassword, UserUpdateRole
from app.services.user import UserService
from app.api.deps import get_current_user
from app.models.user import User
from app.core.limiter import limiter
from app.core.security import verify_password
from app.services.audit import AuditService

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
    Prevents cross-tenant injection and handles global Superadmin bootstrapping.
    """
    db.execute(text('SET search_path TO "public"'))
    
    # Architectural Shield 1: Privilege Escalation Prevention
    if user_in.role == "superadmin" and current_user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Only existing Superadmins can bootstrap new Superadmins."
        )

    # Architectural Shield 2: Tenant Isolation & Global Entity Handling
    if user_in.role == "superadmin":
        # Superadmins must transcend isolated dimensions
        user_in.tenant_id = None
    else:
        # Standard employees must be anchored to a specific dimension
        if not current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Superadmins must provide x-tenant-id header to create tenant employees."
            )
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

@router.patch("/me/password", response_model=UserResponse)
@limiter.limit("5/minute")
def update_own_password(
    request: Request,
    payload: UserUpdatePassword,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Secure password rotation endpoint requiring verification of the current password."""
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Current password verification failed."
        )
    return UserService.update_password(db, user=current_user, new_password=payload.new_password)

@router.patch("/{user_id}/reset-password")
@limiter.limit("5/minute")
def reset_employee_password(
    request: Request, user_id: UUID, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Forces a secure, time-bound password reset for employees.
    Generates a cryptographically strong 12-character password with a 15-minute TTL.
    """
    if current_user.role not in ["admin", "superadmin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges.")

    target_user = UserService.get(db, user_id)
    if not target_user or (target_user.tenant_id != current_user.tenant_id and current_user.role != "superadmin"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    alphabet = string.ascii_letters + string.digits + "!@#$%*"
    while True:
        temp_pwd = ''.join(secrets.choice(alphabet) for _ in range(12))
        if (any(c.islower() for c in temp_pwd) and 
            any(c.isupper() for c in temp_pwd) and 
            sum(c.isdigit() for c in temp_pwd) >= 1 and
            any(c in "!@#$%*" for c in temp_pwd)):
            break

    UserService.force_temp_password(db, user=target_user, temp_password=temp_pwd, expires_in_minutes=15)
    
    return {
        "message": "Temporary password generated successfully.", 
        "temporary_password": temp_pwd,
        "expires_in": "15 minutes"
    }

@router.patch("/{user_id}/role", response_model=UserResponse)
def update_employee_role(
    user_id: UUID,
    payload: UserUpdateRole,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """RBAC escalation endpoint. Protected by strict tenant isolation boundaries."""
    if current_user.role not in ["admin", "superadmin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges.")
    
    if payload.role == "superadmin" and current_user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Only an existing superadmin can elevate a user to superadmin status."
        )

    target_user = UserService.get(db, user_id)
    if not target_user or (target_user.tenant_id != current_user.tenant_id and current_user.role != "superadmin"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Administrators cannot modify their own role. Request superadmin intervention."
        )

    return UserService.update_role(db, user=target_user, new_role=payload.role)

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def soft_delete_employee(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Revokes access by soft-deleting the user entity.
    Maintains relational integrity for historical audit logs.
    """
    if current_user.role not in ["admin", "superadmin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges.")

    target_user = UserService.get(db, user_id)
    if not target_user or (target_user.tenant_id != current_user.tenant_id and current_user.role != "superadmin"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if target_user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Self-deletion is prohibited.")

    if target_user.role == "admin":
        if UserService.count_active_admins(db, target_user.tenant_id) <= 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete the last active administrator.")

    UserService.set_active_status(db, user=target_user, is_active=False)
    
    schema_name = f"tenant_{target_user.tenant.slug}" if target_user.tenant else "public"
    db.execute(text(f'SET search_path TO "{schema_name}"'))
    AuditService.log_action(
        db=db, tenant_id=target_user.tenant_id, user_id=current_user.id,
        action="REVOKE_ACCESS", entity_name="User", entity_id=str(target_user.id),
        changes={"email": target_user.email, "status": "soft_deleted"}
    )
    db.commit()
    return None