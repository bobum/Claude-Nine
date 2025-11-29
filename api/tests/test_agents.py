"""
Tests for agents API endpoints.
"""

import pytest
from uuid import uuid4


class TestAgentsCRUD:
    """Test agents CRUD operations."""

    def test_add_agent_to_team(self, client, sample_team):
        """Test adding an agent to a team."""
        team_id = sample_team["id"]
        response = client.post(f"/api/teams/{team_id}/agents", json={
            "name": "Developer Agent",
            "persona_type": "dev",
            "role": "Software Developer",
            "goal": "Write clean code"
        })

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Developer Agent"
        assert data["persona_type"] == "dev"
        assert data["team_id"] == team_id

    def test_add_agent_minimal_fields(self, client, sample_team):
        """Test adding an agent with minimal required fields."""
        team_id = sample_team["id"]
        response = client.post(f"/api/teams/{team_id}/agents", json={
            "name": "Minimal Agent",
            "persona_type": "dev",
            "role": "Developer"
        })

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal Agent"
        assert data["role"] == "Developer"

    def test_add_agent_duplicate_name(self, client, sample_team, sample_agent):
        """Test that duplicate agent names in same team are rejected."""
        team_id = sample_team["id"]
        response = client.post(f"/api/teams/{team_id}/agents", json={
            "name": sample_agent["name"],  # Same name
            "persona_type": "dev",
            "role": "Another Developer"
        })

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_add_agent_invalid_persona(self, client, sample_team):
        """Test that invalid persona types are rejected."""
        team_id = sample_team["id"]
        response = client.post(f"/api/teams/{team_id}/agents", json={
            "name": "Invalid Agent",
            "persona_type": "invalid_type",
            "role": "Developer"
        })

        assert response.status_code == 400

    def test_add_agent_to_nonexistent_team(self, client):
        """Test adding an agent to a non-existent team."""
        fake_team_id = str(uuid4())
        response = client.post(f"/api/teams/{fake_team_id}/agents", json={
            "name": "Orphan Agent",
            "persona_type": "dev",
            "role": "Developer"
        })

        assert response.status_code == 404

    def test_get_agent(self, client, sample_agent):
        """Test getting a specific agent."""
        agent_id = sample_agent["id"]
        response = client.get(f"/api/agents/{agent_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == agent_id
        assert data["name"] == sample_agent["name"]

    def test_get_agent_not_found(self, client):
        """Test getting a non-existent agent."""
        fake_id = str(uuid4())
        response = client.get(f"/api/agents/{fake_id}")

        assert response.status_code == 404

    def test_delete_agent(self, client, sample_agent):
        """Test deleting an agent."""
        agent_id = sample_agent["id"]
        response = client.delete(f"/api/agents/{agent_id}")

        assert response.status_code == 204

        # Verify it's deleted
        response = client.get(f"/api/agents/{agent_id}")
        assert response.status_code == 404

    def test_list_agents(self, client, sample_agent):
        """Test listing all agents."""
        response = client.get("/api/agents/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_list_agents_by_team(self, client, sample_team, sample_agent):
        """Test listing agents filtered by team."""
        team_id = sample_team["id"]
        response = client.get(f"/api/agents/?team_id={team_id}")

        assert response.status_code == 200
        data = response.json()
        assert all(a["team_id"] == team_id for a in data)


class TestAgentPersonas:
    """Test agent persona types."""

    def test_list_personas(self, client):
        """Test listing available personas."""
        response = client.get("/api/personas/")

        assert response.status_code == 200
        data = response.json()
        # API returns {"personas": [...]}
        assert "personas" in data
        personas = data["personas"]
        assert isinstance(personas, list)
        # Should have at least dev persona
        assert any(p.get("type") == "dev" or p.get("display_name") == "Developer" for p in personas)

    def test_dev_persona_exists(self, client):
        """Test that dev persona is available."""
        response = client.get("/api/personas/")

        assert response.status_code == 200
        data = response.json()
        personas = data["personas"]
        # Find dev persona by type or display_name
        dev_personas = [p for p in personas if p.get("type") == "dev" or p.get("display_name") == "Developer"]
        assert len(dev_personas) >= 1


class TestAgentStatus:
    """Test agent status."""

    def test_agent_default_status(self, client, sample_agent):
        """Test that new agents have idle status."""
        assert sample_agent["status"] == "idle"

    def test_get_agent_status(self, client, sample_agent):
        """Test getting agent status details."""
        agent_id = sample_agent["id"]
        response = client.get(f"/api/agents/{agent_id}/status")

        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == agent_id
        assert data["status"] == "idle"
        assert "name" in data
