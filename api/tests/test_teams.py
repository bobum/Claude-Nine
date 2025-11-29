"""
Tests for teams API endpoints.
"""

import pytest
from uuid import uuid4


class TestTeamsCRUD:
    """Test teams CRUD operations."""

    def test_create_team(self, client, temp_git_repo):
        """Test creating a new team."""
        response = client.post("/api/teams/", json={
            "name": "New Team",
            "product": "New Product",
            "repo_path": temp_git_repo,
            "main_branch": "main"
        })

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Team"
        assert data["product"] == "New Product"
        assert data["repo_path"] == temp_git_repo
        assert "id" in data

    def test_create_team_duplicate_name(self, client, sample_team, temp_git_repo):
        """Test that duplicate team names are rejected."""
        response = client.post("/api/teams/", json={
            "name": sample_team["name"],  # Same name
            "product": "Another Product",
            "repo_path": temp_git_repo
        })

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_list_teams(self, client, sample_team):
        """Test listing all teams."""
        response = client.get("/api/teams/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(t["id"] == sample_team["id"] for t in data)

    def test_get_team(self, client, sample_team):
        """Test getting a specific team."""
        team_id = sample_team["id"]
        response = client.get(f"/api/teams/{team_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == team_id
        assert data["name"] == sample_team["name"]

    def test_get_team_not_found(self, client):
        """Test getting a non-existent team."""
        fake_id = str(uuid4())
        response = client.get(f"/api/teams/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_team(self, client, sample_team):
        """Test updating a team."""
        team_id = sample_team["id"]
        response = client.put(f"/api/teams/{team_id}", json={
            "product": "Updated Product"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["product"] == "Updated Product"
        assert data["name"] == sample_team["name"]  # Unchanged

    def test_delete_team(self, client, sample_team):
        """Test deleting a team."""
        team_id = sample_team["id"]
        response = client.delete(f"/api/teams/{team_id}")

        assert response.status_code == 204

        # Verify it's deleted
        response = client.get(f"/api/teams/{team_id}")
        assert response.status_code == 404


class TestTeamReadiness:
    """Test team readiness endpoint."""

    def test_readiness_no_agents(self, client, sample_team):
        """Test readiness when team has no agents."""
        team_id = sample_team["id"]
        response = client.get(f"/api/teams/{team_id}/readiness")

        assert response.status_code == 200
        data = response.json()
        assert data["is_ready"] is False
        assert data["checks"]["has_agents"] is False
        assert "No agents" in str(data["issues"])

    def test_readiness_no_work_items(self, client, sample_team, sample_agent):
        """Test readiness when team has no work items."""
        team_id = sample_team["id"]
        response = client.get(f"/api/teams/{team_id}/readiness")

        assert response.status_code == 200
        data = response.json()
        assert data["is_ready"] is False
        assert data["checks"]["has_queued_work"] is False

    def test_readiness_fully_ready(self, client, sample_team, sample_agent, sample_work_item):
        """Test readiness when team is fully configured."""
        team_id = sample_team["id"]
        response = client.get(f"/api/teams/{team_id}/readiness")

        assert response.status_code == 200
        data = response.json()
        assert data["is_ready"] is True
        assert data["checks"]["has_agents"] is True
        assert data["checks"]["has_queued_work"] is True
        assert data["checks"]["is_git_repository"] is True


class TestTeamOrchestrator:
    """Test team orchestrator start/stop with mocked service."""

    def test_start_team_success(self, client, sample_team, sample_agent, sample_work_item, mock_orchestrator_service):
        """Test starting a team successfully."""
        team_id = sample_team["id"]
        response = client.post(f"/api/teams/{team_id}/start")

        assert response.status_code == 200
        data = response.json()
        assert "started" in data["message"].lower() or data["orchestrator_status"] == "started"
        mock_orchestrator_service.start_team.assert_called_once()

    def test_start_team_no_agents(self, client, sample_team, mock_orchestrator_service):
        """Test starting a team without agents fails."""
        team_id = sample_team["id"]
        response = client.post(f"/api/teams/{team_id}/start")

        assert response.status_code == 400
        assert "No agents" in response.json()["detail"]

    def test_start_team_no_work_items(self, client, sample_team, sample_agent, mock_orchestrator_service):
        """Test starting a team without work items fails."""
        team_id = sample_team["id"]
        response = client.post(f"/api/teams/{team_id}/start")

        assert response.status_code == 400
        assert "No work items" in response.json()["detail"]

    def test_stop_team(self, client, sample_team, mock_orchestrator_service):
        """Test stopping a team."""
        team_id = sample_team["id"]
        response = client.post(f"/api/teams/{team_id}/stop")

        assert response.status_code == 200
        data = response.json()
        assert data["orchestrator_status"] == "stopped"
        mock_orchestrator_service.stop_team.assert_called_once()

    def test_get_orchestrator_status(self, client, sample_team, mock_orchestrator_service):
        """Test getting orchestrator status."""
        team_id = sample_team["id"]
        response = client.get(f"/api/teams/{team_id}/orchestrator-status")

        assert response.status_code == 200
        data = response.json()
        assert "running" in data
        mock_orchestrator_service.get_status.assert_called_once()
