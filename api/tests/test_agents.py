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

    def test_add_agent_with_auto_role(self, client, sample_team):
        """Test adding an agent with auto-generated role from persona."""
        team_id = sample_team["id"]
        response = client.post(f"/api/teams/{team_id}/agents", json={
            "name": "Auto Role Agent",
            "persona_type": "dev"
        })

        assert response.status_code == 201
        data = response.json()
        # Should have auto-generated role from dev persona
        assert data["role"] is not None
        assert len(data["role"]) > 0

    def test_add_agent_duplicate_name(self, client, sample_team, sample_agent):
        """Test that duplicate agent names in same team are rejected."""
        team_id = sample_team["id"]
        response = client.post(f"/api/teams/{team_id}/agents", json={
            "name": sample_agent["name"],  # Same name
            "persona_type": "dev"
        })

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_add_agent_invalid_persona(self, client, sample_team):
        """Test that invalid persona types are rejected."""
        team_id = sample_team["id"]
        response = client.post(f"/api/teams/{team_id}/agents", json={
            "name": "Invalid Agent",
            "persona_type": "invalid_type"
        })

        assert response.status_code == 400

    def test_add_agent_to_nonexistent_team(self, client):
        """Test adding an agent to a non-existent team."""
        fake_team_id = str(uuid4())
        response = client.post(f"/api/teams/{fake_team_id}/agents", json={
            "name": "Orphan Agent",
            "persona_type": "dev"
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

    def test_update_agent(self, client, sample_agent):
        """Test updating an agent."""
        agent_id = sample_agent["id"]
        response = client.put(f"/api/agents/{agent_id}", json={
            "role": "Senior Developer",
            "goal": "Mentor junior devs and write code"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "Senior Developer"
        assert data["goal"] == "Mentor junior devs and write code"

    def test_delete_agent(self, client, sample_agent):
        """Test deleting an agent."""
        agent_id = sample_agent["id"]
        response = client.delete(f"/api/agents/{agent_id}")

        assert response.status_code == 204

        # Verify it's deleted
        response = client.get(f"/api/agents/{agent_id}")
        assert response.status_code == 404


class TestAgentPersonas:
    """Test agent persona types."""

    def test_list_personas(self, client):
        """Test listing available personas."""
        response = client.get("/api/personas/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have at least dev persona
        assert any(p["type"] == "dev" for p in data)

    def test_dev_persona_exists(self, client):
        """Test that dev persona is available."""
        response = client.get("/api/personas/")

        assert response.status_code == 200
        data = response.json()
        dev_personas = [p for p in data if p["type"] == "dev"]
        assert len(dev_personas) == 1
        assert dev_personas[0]["name"] == "Developer"


class TestAgentStatus:
    """Test agent status updates."""

    def test_agent_default_status(self, client, sample_agent):
        """Test that new agents have idle status."""
        assert sample_agent["status"] == "idle"

    def test_update_agent_status(self, client, sample_agent):
        """Test updating agent status."""
        agent_id = sample_agent["id"]
        response = client.put(f"/api/agents/{agent_id}", json={
            "status": "working"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "working"
