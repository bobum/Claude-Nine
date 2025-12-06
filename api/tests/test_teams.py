"""
Tests for Teams API endpoints.

Covers:
- CRUD operations (Create, Read, Update, Delete)
- Validation errors
- Edge cases
"""

import pytest
from uuid import uuid4


class TestListTeams:
    """Tests for GET /api/teams/"""

    def test_list_teams_empty(self, client):
        """List teams returns empty list when no teams exist."""
        response = client.get("/api/teams/")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_teams_with_data(self, client, sample_team_data):
        """List teams returns created teams."""
        # Create a team first
        client.post("/api/teams/", json=sample_team_data)

        response = client.get("/api/teams/")
        assert response.status_code == 200
        teams = response.json()
        assert len(teams) == 1
        assert teams[0]["name"] == sample_team_data["name"]

    def test_list_teams_pagination(self, client, sample_team_data):
        """List teams supports skip and limit parameters."""
        # Create multiple teams
        for i in range(5):
            data = {**sample_team_data, "name": f"Team {i}"}
            client.post("/api/teams/", json=data)

        # Test limit
        response = client.get("/api/teams/?limit=2")
        assert response.status_code == 200
        assert len(response.json()) == 2

        # Test skip
        response = client.get("/api/teams/?skip=3")
        assert response.status_code == 200
        assert len(response.json()) == 2  # 5 total - 3 skipped = 2


class TestGetTeam:
    """Tests for GET /api/teams/{team_id}"""

    def test_get_team_success(self, client, created_team):
        """Get team by ID returns team with agents."""
        team_id = created_team["id"]
        response = client.get(f"/api/teams/{team_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == team_id
        assert data["name"] == created_team["name"]
        assert "agents" in data  # TeamWithAgents includes agents

    def test_get_team_not_found(self, client):
        """Get nonexistent team returns 404."""
        fake_id = str(uuid4())
        response = client.get(f"/api/teams/{fake_id}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestGetTeamFull:
    """Tests for GET /api/teams/{team_id}/full"""

    def test_get_team_full_success(self, client, created_team):
        """Get full team details includes agents and work items."""
        team_id = created_team["id"]
        response = client.get(f"/api/teams/{team_id}/full")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == team_id
        assert "agents" in data
        assert "work_items" in data

    def test_get_team_full_not_found(self, client):
        """Get full details of nonexistent team returns 404."""
        fake_id = str(uuid4())
        response = client.get(f"/api/teams/{fake_id}/full")
        assert response.status_code == 404


class TestCreateTeam:
    """Tests for POST /api/teams/"""

    def test_create_team_success(self, client, sample_team_data):
        """Create team with valid data succeeds."""
        response = client.post("/api/teams/", json=sample_team_data)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_team_data["name"]
        assert data["product"] == sample_team_data["product"]
        assert data["repo_path"] == sample_team_data["repo_path"]
        assert data["status"] == "stopped"  # Default status
        assert "id" in data
        assert "created_at" in data

    def test_create_team_duplicate_name(self, client, sample_team_data):
        """Create team with duplicate name fails."""
        # Create first team
        client.post("/api/teams/", json=sample_team_data)

        # Try to create duplicate
        response = client.post("/api/teams/", json=sample_team_data)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_create_team_missing_required_fields(self, client):
        """Create team with missing required fields fails."""
        response = client.post("/api/teams/", json={})
        assert response.status_code == 422  # Validation error

    def test_create_team_empty_name(self, client, sample_team_data):
        """Create team with empty name fails validation."""
        data = {**sample_team_data, "name": ""}
        response = client.post("/api/teams/", json=data)
        assert response.status_code == 422

    def test_create_team_default_values(self, client):
        """Create team uses default values when not provided."""
        minimal_data = {
            "name": "Minimal Team",
            "product": "Minimal Product",
            "repo_path": "/tmp/minimal"
        }
        response = client.post("/api/teams/", json=minimal_data)
        assert response.status_code == 201
        data = response.json()
        assert data["main_branch"] == "main"
        assert data["max_concurrent_tasks"] == 4


class TestUpdateTeam:
    """Tests for PUT /api/teams/{team_id}"""

    def test_update_team_success(self, client, created_team):
        """Update team with valid data succeeds."""
        team_id = created_team["id"]
        update_data = {"name": "Updated Team Name"}

        response = client.put(f"/api/teams/{team_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Team Name"
        assert data["product"] == created_team["product"]  # Unchanged

    def test_update_team_status(self, client, created_team):
        """Update team status."""
        team_id = created_team["id"]
        update_data = {"status": "paused"}

        response = client.put(f"/api/teams/{team_id}", json=update_data)
        assert response.status_code == 200
        assert response.json()["status"] == "paused"

    def test_update_team_not_found(self, client):
        """Update nonexistent team returns 404."""
        fake_id = str(uuid4())
        response = client.put(f"/api/teams/{fake_id}", json={"name": "New Name"})
        assert response.status_code == 404

    def test_update_team_partial(self, client, created_team):
        """Update team with partial data only updates provided fields."""
        team_id = created_team["id"]
        original_product = created_team["product"]

        response = client.put(
            f"/api/teams/{team_id}",
            json={"max_concurrent_tasks": 10}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["max_concurrent_tasks"] == 10
        assert data["product"] == original_product  # Unchanged


class TestDeleteTeam:
    """Tests for DELETE /api/teams/{team_id}"""

    def test_delete_team_success(self, client, created_team):
        """Delete team succeeds."""
        team_id = created_team["id"]
        response = client.delete(f"/api/teams/{team_id}")
        assert response.status_code == 204

        # Verify team is deleted
        get_response = client.get(f"/api/teams/{team_id}")
        assert get_response.status_code == 404

    def test_delete_team_not_found(self, client):
        """Delete nonexistent team returns 404."""
        fake_id = str(uuid4())
        response = client.delete(f"/api/teams/{fake_id}")
        assert response.status_code == 404


class TestTeamReadiness:
    """Tests for GET /api/teams/{team_id}/readiness"""

    def test_readiness_no_repo(self, client, sample_team_data):
        """Readiness check fails when repo doesn't exist."""
        # Create team with non-existent repo
        data = {**sample_team_data, "repo_path": "/nonexistent/path"}
        response = client.post("/api/teams/", json=data)
        team_id = response.json()["id"]

        readiness = client.get(f"/api/teams/{team_id}/readiness")
        assert readiness.status_code == 200
        data = readiness.json()
        assert data["is_ready"] is False
        assert data["checks"]["repository_exists"] is False
        assert len(data["issues"]) > 0

    def test_readiness_no_work(self, client, created_team):
        """Readiness check fails when no queued work items."""
        team_id = created_team["id"]
        readiness = client.get(f"/api/teams/{team_id}/readiness")
        assert readiness.status_code == 200
        data = readiness.json()
        assert data["checks"]["has_queued_work"] is False

    def test_readiness_not_found(self, client):
        """Readiness check on nonexistent team returns 404."""
        fake_id = str(uuid4())
        response = client.get(f"/api/teams/{fake_id}/readiness")
        assert response.status_code == 404
