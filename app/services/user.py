from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import get_password_hash, verify_password

class UserService:
    """
    Service responsible for global user management within the 'public' schema.
    Ensures authentication remains isolated from tenant-specific data contexts.
    """

    @staticmethod
    def get_by_email(db: Session, email: str) -> User | None:
        """
        Retrieves a user by email, enforcing context on the 'public' schema.
        """
        db.execute(text('SET search_path TO "public"'))
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def authenticate(db: Session, email: str, password: str) -> User | None:
        """
        Verifies credentials against the global user record.
        """
        user = UserService.get_by_email(db, email)
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    def create(db: Session, user_in: UserCreate) -> User:
        """
        Provisions a new user in the global 'public' table.
        """
        db.execute(text('SET search_path TO "public"'))
        hashed_pw = get_password_hash(user_in.password)
        db_user = User(
            tenant_id=user_in.tenant_id,
            email=user_in.email,
            hashed_password=hashed_pw,
            full_name=user_in.full_name,
            role=user_in.role
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user