import pytest
import redis
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database

from app.main import app
from app.db.session import get_db
from app.models import Base
from app.core.config import settings

TEST_ADMIN_PASSWORD = "SecurePassword123!"

base_url = settings.DATABASE_URL.rsplit("/", 1)[0]
SQLALCHEMY_DATABASE_URL = f"{base_url}/nexcore_test"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(autouse=True)
def reset_rate_limits():
    """
    Architectural Fix: Prevents Test Pollution (Rate Limiter Exhaustion).
    Flushes the Redis cache before each test to guarantee deterministic HTTP responses.
    """
    try:
        r = redis.from_url(settings.REDIS_URL)
        r.flushdb()
    except Exception:
        pass
    yield

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    if not database_exists(engine.url):
        create_database(engine.url)
    
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db() -> Generator:
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db) -> Generator:
    def _get_test_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _get_test_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def default_password() -> str:
    """Fixture providing a deterministic strong password fulfilling Pydantic requirements."""
    return TEST_ADMIN_PASSWORD