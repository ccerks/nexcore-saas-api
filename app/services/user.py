from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import get_password_hash, verify_password

class UserService:
    @staticmethod
    def get_by_email(db: Session, email: str) -> User | None:
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def create(db: Session, user_in: UserCreate) -> User:
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

    @staticmethod
    def authenticate(db: Session, email: str, password: str) -> User | None:
        """Verify user credentials."""
        user = UserService.get_by_email(db, email)
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user