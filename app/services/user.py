from sqlalchemy.orm import Session
from sqlalchemy import text
from uuid import UUID
from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import get_password_hash, verify_password
from datetime import datetime, timedelta, timezone

class UserService:
    """
    Service responsible for global Identity and Access Management (IAM) 
    within the isolated 'public' schema context.
    """

    @staticmethod
    def get(db: Session, user_id: UUID) -> User | None:
        """Retrieves a user by their exact UUID."""
        db.execute(text('SET search_path TO "public"'))
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> User | None:
        db.execute(text('SET search_path TO "public"'))
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_by_username(db: Session, username: str) -> User | None:
        """Architectural Fix: Lookup via friendly identifier for UX operations."""
        db.execute(text('SET search_path TO "public"'))
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def authenticate(db: Session, email: str, password: str) -> User | None:
        """Verifies credentials and enforces strict temporary password TTL."""
        user = UserService.get_by_email(db, email)
        if not user or not verify_password(password, user.hashed_password):
            return None
            
        # Security Gate: Block login if the temporary password has expired
        if user.password_expires_at and datetime.now(timezone.utc) > user.password_expires_at:
            return None
            
        return user

    @staticmethod
    def create(db: Session, user_in: UserCreate) -> User:
        db.execute(text('SET search_path TO "public"'))
        hashed_pw = get_password_hash(user_in.password)
        
        # Architectural Mapping: The username must be injected here
        db_user = User(
            tenant_id=user_in.tenant_id,
            username=user_in.username,
            email=user_in.email,
            hashed_password=hashed_pw,
            full_name=user_in.full_name,
            role=user_in.role
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def update_password(db: Session, user: User, new_password: str) -> User:
        """Rotates password and clears any existing expiration locks."""
        db.execute(text('SET search_path TO "public"'))
        user.hashed_password = get_password_hash(new_password)
        user.password_expires_at = None
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update_role(db: Session, user: User, new_role: str) -> User:
        """Escalates or de-escalates RBAC privileges."""
        db.execute(text('SET search_path TO "public"'))
        user.role = new_role
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def set_active_status(db: Session, user: User, is_active: bool) -> User:
        """
        Toggles operational access. Setting to False acts as a Soft Delete,
        preserving referential integrity in audit logs.
        """
        db.execute(text('SET search_path TO "public"'))
        user.is_active = is_active
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def count_active_admins(db: Session, tenant_id: UUID) -> int:
        db.execute(text('SET search_path TO "public"'))
        return db.query(User).filter(
            User.tenant_id == tenant_id, 
            User.role == "admin", 
            User.is_active == True
        ).count()
    
    @staticmethod
    def force_temp_password(db: Session, user: User, temp_password: str, expires_in_minutes: int = 15) -> User:
        """Generates a time-bound hash for administrative resets."""
        db.execute(text('SET search_path TO "public"'))
        user.hashed_password = get_password_hash(temp_password)
        user.password_expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
        db.commit()
        db.refresh(user)
        return user