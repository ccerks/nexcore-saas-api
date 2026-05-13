import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database

from app.main import app
from app.db.session import get_db
from app.models import Base
from app.core.config import settings

# Dynamically builds the test database URL using credentials from the .env file.
# Slices the original URL at the last '/' and appends the test database name.
base_url = settings.DATABASE_URL.rsplit("/", 1)[0]
SQLALCHEMY_DATABASE_URL = f"{base_url}/nexcore_test"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """
    Creates a clean test database and tables before the test session starts.
    """
    if not database_exists(engine.url):
        create_database(engine.url)
    
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db() -> Generator:
    """
    Provides a transactional database session for each test.
    Rolls back changes after each test to maintain isolation.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db) -> Generator:
    """
    Overrides the database dependency and returns a TestClient.
    """
    def _get_test_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _get_test_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()