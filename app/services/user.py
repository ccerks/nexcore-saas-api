from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import get_password_hash

class UserService:
    """
    Handles all business logic, password hashing, and database operations for Users.
    """
    
    @staticmethod
    def get_by_email(db: Session, email: str) -> User | None:
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def create(db: Session, user_in: UserCreate) -> User:
        # 1. Hash the plain text password
        hashed_pw = get_password_hash(user_in.password)
        
        # 2. Build the database model, replacing 'password' with 'hashed_password'
        db_user = User(
            tenant_id=user_in.tenant_id,
            email=user_in.email,
            hashed_password=hashed_pw,
            full_name=user_in.full_name,
            role=user_in.role
        )
        
        # 3. Persist to the database
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user