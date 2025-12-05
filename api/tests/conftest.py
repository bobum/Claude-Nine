"""
Pytest fixtures for API tests.

Provides:
- In-memory SQLite test database
- FastAPI TestClient with database override
- Common test data fixtures
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import sys
from pathlib import Path

# Add project root to path for shared imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from api.app.database import Base, get_db
from api.app.main import app


# Create in-memory SQLite database for testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    """Override database dependency with test database."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    # Create all tables
    Base.metadata.create_all(bind=test_engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database override."""
    # Override the database dependency
    app.dependency_overrides[get_db] = override_get_db

    # Create tables
    Base.metadata.create_all(bind=test_engine)

    with TestClient(app) as test_client:
        yield test_client

    # Clean up
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def sample_team_data():
    """Sample team data for testing."""
    return {
        "name": "Test Team",
        "product": "Test Product",
        "repo_path": "/tmp/test-repo",
        "main_branch": "main",
        "max_concurrent_tasks": 4
    }


@pytest.fixture
def sample_work_item_data():
    """Sample work item data for testing."""
    return {
        "external_id": "TEST-123",
        "source": "manual",
        "title": "Test Work Item",
        "description": "Test description",
        "priority": 1
    }


@pytest.fixture
def created_team(client, sample_team_data):
    """Create and return a team for tests that need an existing team."""
    response = client.post("/api/teams/", json=sample_team_data)
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def created_work_item(client, sample_work_item_data, created_team):
    """Create and return a work item assigned to a team."""
    data = {**sample_work_item_data, "team_id": created_team["id"]}
    response = client.post("/api/work-items/", json=data)
    assert response.status_code == 201
    return response.json()
