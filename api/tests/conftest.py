"""
Pytest fixtures for API tests.

Provides test database, test client, and mock fixtures.
"""

import pytest
import tempfile
import os
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import Base, get_db
from app.main import app


# Create an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    # Create all tables
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize git repo
        os.system(f'cd "{tmpdir}" && git init --quiet')
        os.system(f'cd "{tmpdir}" && git config user.email "test@test.com"')
        os.system(f'cd "{tmpdir}" && git config user.name "Test"')

        # Create initial commit
        readme_path = os.path.join(tmpdir, "README.md")
        with open(readme_path, "w") as f:
            f.write("# Test Repo\n")
        os.system(f'cd "{tmpdir}" && git add . && git commit -m "Initial commit" --quiet')

        yield tmpdir


@pytest.fixture
def mock_orchestrator_service():
    """Mock the orchestrator service to avoid spinning up real agents."""
    mock_service = MagicMock()
    mock_service.start_team.return_value = {
        "status": "started",
        "message": "Orchestrator started (mocked)",
        "work_items_count": 1,
        "agents_count": 1
    }
    mock_service.stop_team.return_value = {
        "status": "stopped",
        "message": "Orchestrator stopped (mocked)"
    }
    mock_service.get_status.return_value = {
        "running": False,
        "message": "Orchestrator not running"
    }

    # Patch where the function is imported, not where it's defined
    with patch('app.services.orchestrator_service.get_orchestrator_service', return_value=mock_service):
        yield mock_service


@pytest.fixture
def sample_team(client, temp_git_repo):
    """Create a sample team for testing."""
    response = client.post("/api/teams/", json={
        "name": "Test Team",
        "product": "Test Product",
        "repo_path": temp_git_repo,
        "main_branch": "main"
    })
    assert response.status_code == 201, f"Failed to create team: {response.json()}"
    return response.json()


@pytest.fixture
def sample_agent(client, sample_team):
    """Create a sample agent for testing."""
    team_id = sample_team["id"]
    response = client.post(f"/api/teams/{team_id}/agents", json={
        "name": "Test Agent",
        "persona_type": "dev",
        "role": "Developer",
        "goal": "Implement features"
    })
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def sample_work_item(client, sample_team):
    """Create a sample work item for testing."""
    team_id = sample_team["id"]
    response = client.post("/api/work-items/", json={
        "external_id": "PBI-001",
        "source": "manual",
        "title": "Test Work Item",
        "description": "A test task",
        "team_id": team_id,
        "priority": 1
    })
    assert response.status_code == 201, f"Failed to create work item: {response.json()}"
    return response.json()
