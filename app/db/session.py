from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.orm import Session
import os

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    Yields a database session that defaults to the 'public' schema.
    Essential for globally querying Tenants and Users before routing.
    """
    db = SessionLocal()
    try:
        db.execute(text('SET search_path TO "public"'))
        yield db
    finally:
        db.close()

def set_tenant_schema(db: Session, tenant_slug: str) -> None:
    """
    Dynamically switches the PostgreSQL search_path to the tenant's dedicated schema.
    Falls back to 'public' for shared tables (like Users).
    """
    schema_name = f"tenant_{tenant_slug}"
    db.execute(text(f'SET search_path TO "{schema_name}", "public"'))