"""
Tests for work items API endpoints.
"""

import pytest
from uuid import uuid4


class TestWorkItemsCRUD:
    """Test work items CRUD operations."""

    def test_create_work_item(self, client, sample_team):
        """Test creating a new work item."""
        team_id = sample_team["id"]
        response = client.post("/api/work-items/", json={
            "external_id": "TASK-001",
            "source": "manual",
            "title": "New Feature",
            "description": "Implement a new feature",
            "team_id": team_id,
            "priority": 1
        })

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Feature"
        assert data["status"] == "queued"
        assert data["team_id"] == team_id
        assert "id" in data

    def test_create_work_item_with_external_id(self, client, sample_team):
        """Test creating a work item with Azure DevOps source."""
        team_id = sample_team["id"]
        response = client.post("/api/work-items/", json={
            "external_id": "PBI-001",
            "source": "azure_devops",
            "title": "PBI-001: User Login",
            "description": "Implement user login",
            "team_id": team_id
        })

        assert response.status_code == 201
        data = response.json()
        assert data["external_id"] == "PBI-001"
        assert data["source"] == "azure_devops"

    def test_list_work_items(self, client, sample_work_item):
        """Test listing all work items."""
        response = client.get("/api/work-items/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_list_work_items_by_team(self, client, sample_team, sample_work_item):
        """Test listing work items filtered by team."""
        team_id = sample_team["id"]
        response = client.get(f"/api/work-items/?team_id={team_id}")

        assert response.status_code == 200
        data = response.json()
        assert all(item["team_id"] == team_id for item in data)

    def test_list_work_items_by_status(self, client, sample_work_item):
        """Test listing work items filtered by status."""
        response = client.get("/api/work-items/?status=queued")

        assert response.status_code == 200
        data = response.json()
        assert all(item["status"] == "queued" for item in data)

    def test_get_work_item(self, client, sample_work_item):
        """Test getting a specific work item."""
        work_item_id = sample_work_item["id"]
        response = client.get(f"/api/work-items/{work_item_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == work_item_id

    def test_get_work_item_not_found(self, client):
        """Test getting a non-existent work item."""
        fake_id = str(uuid4())
        response = client.get(f"/api/work-items/{fake_id}")

        assert response.status_code == 404

    def test_update_work_item(self, client, sample_work_item):
        """Test updating a work item."""
        work_item_id = sample_work_item["id"]
        response = client.put(f"/api/work-items/{work_item_id}", json={
            "status": "in_progress",
            "priority": 2
        })

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"
        assert data["priority"] == 2

    def test_delete_work_item(self, client, sample_work_item):
        """Test deleting a work item."""
        work_item_id = sample_work_item["id"]
        response = client.delete(f"/api/work-items/{work_item_id}")

        assert response.status_code == 204

        # Verify it's deleted
        response = client.get(f"/api/work-items/{work_item_id}")
        assert response.status_code == 404


class TestWorkItemAssignment:
    """Test work item assignment to teams."""

    def test_assign_work_item_to_team(self, client, sample_team):
        """Test assigning a work item to a team."""
        # Create unassigned work item
        response = client.post("/api/work-items/", json={
            "external_id": "TASK-002",
            "source": "manual",
            "title": "Unassigned Task",
            "description": "A task without a team"
        })
        assert response.status_code == 201
        work_item_id = response.json()["id"]

        # Assign to team
        team_id = sample_team["id"]
        response = client.put(f"/api/work-items/{work_item_id}", json={
            "team_id": team_id
        })

        assert response.status_code == 200
        data = response.json()
        assert data["team_id"] == team_id

    def test_change_work_item_status(self, client, sample_work_item):
        """Test changing work item status through workflow."""
        work_item_id = sample_work_item["id"]

        # queued -> in_progress
        response = client.put(f"/api/work-items/{work_item_id}", json={
            "status": "in_progress"
        })
        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"

        # in_progress -> completed
        response = client.put(f"/api/work-items/{work_item_id}", json={
            "status": "completed"
        })
        assert response.status_code == 200
        assert response.json()["status"] == "completed"
