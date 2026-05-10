from passlib.context import CryptContext

# Define the hashing algorithm (bcrypt is the industry standard)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against a hashed password.
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Generates a bcrypt hash from a plain-text password.
    """
    return pwd_context.hash(password)