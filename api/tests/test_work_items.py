"""
Tests for Work Items API endpoints.

Covers:
- CRUD operations
- Filtering by team, status, source
- Bulk assignment
- Validation
"""

import pytest
from uuid import uuid4


class TestListWorkItems:
    """Tests for GET /api/work-items/"""

    def test_list_work_items_empty(self, client):
        """List work items returns empty list when none exist."""
        response = client.get("/api/work-items/")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_work_items_with_data(self, client, created_work_item):
        """List work items returns created items."""
        response = client.get("/api/work-items/")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 1
        assert items[0]["title"] == created_work_item["title"]

    def test_list_work_items_filter_by_team(self, client, created_work_item, sample_work_item_data):
        """List work items can filter by team_id."""
        team_id = created_work_item["team_id"]

        # Create another work item without team
        other_data = {**sample_work_item_data, "external_id": "OTHER-123"}
        client.post("/api/work-items/", json=other_data)

        # Filter by team
        response = client.get(f"/api/work-items/?team_id={team_id}")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 1
        assert items[0]["team_id"] == team_id

    def test_list_work_items_filter_by_status(self, client, created_work_item):
        """List work items can filter by status."""
        response = client.get("/api/work-items/?status=queued")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 1

        response = client.get("/api/work-items/?status=completed")
        assert response.status_code == 200
        assert len(response.json()) == 0

    def test_list_work_items_filter_by_source(self, client, created_work_item):
        """List work items can filter by source."""
        response = client.get("/api/work-items/?source=manual")
        assert response.status_code == 200
        assert len(response.json()) == 1

        response = client.get("/api/work-items/?source=jira")
        assert response.status_code == 200
        assert len(response.json()) == 0

    def test_list_work_items_pagination(self, client, created_team, sample_work_item_data):
        """List work items supports pagination."""
        # Create multiple items
        for i in range(5):
            data = {
                **sample_work_item_data,
                "external_id": f"TEST-{i}",
                "team_id": created_team["id"]
            }
            client.post("/api/work-items/", json=data)

        response = client.get("/api/work-items/?limit=2")
        assert response.status_code == 200
        assert len(response.json()) == 2


class TestGetWorkItem:
    """Tests for GET /api/work-items/{work_item_id}"""

    def test_get_work_item_success(self, client, created_work_item):
        """Get work item by ID succeeds."""
        item_id = created_work_item["id"]
        response = client.get(f"/api/work-items/{item_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == item_id
        assert data["title"] == created_work_item["title"]

    def test_get_work_item_not_found(self, client):
        """Get nonexistent work item returns 404."""
        fake_id = str(uuid4())
        response = client.get(f"/api/work-items/{fake_id}")
        assert response.status_code == 404


class TestCreateWorkItem:
    """Tests for POST /api/work-items/"""

    def test_create_work_item_success(self, client, sample_work_item_data):
        """Create work item with valid data succeeds."""
        response = client.post("/api/work-items/", json=sample_work_item_data)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == sample_work_item_data["title"]
        assert data["external_id"] == sample_work_item_data["external_id"]
        assert data["status"] == "queued"  # Default status
        assert "id" in data

    def test_create_work_item_with_team(self, client, sample_work_item_data, created_team):
        """Create work item assigned to a team."""
        data = {**sample_work_item_data, "team_id": created_team["id"]}
        response = client.post("/api/work-items/", json=data)
        assert response.status_code == 201
        assert response.json()["team_id"] == created_team["id"]

    def test_create_work_item_duplicate(self, client, sample_work_item_data):
        """Create work item with duplicate source+external_id fails."""
        # Create first
        client.post("/api/work-items/", json=sample_work_item_data)

        # Try duplicate
        response = client.post("/api/work-items/", json=sample_work_item_data)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_create_work_item_all_sources(self, client, sample_work_item_data):
        """Create work items from all valid sources."""
        sources = ["azure_devops", "jira", "github", "linear", "manual"]
        for i, source in enumerate(sources):
            data = {
                **sample_work_item_data,
                "external_id": f"SRC-{i}",
                "source": source
            }
            response = client.post("/api/work-items/", json=data)
            assert response.status_code == 201
            assert response.json()["source"] == source

    def test_create_work_item_missing_required(self, client):
        """Create work item with missing required fields fails."""
        response = client.post("/api/work-items/", json={})
        assert response.status_code == 422


class TestUpdateWorkItem:
    """Tests for PUT /api/work-items/{work_item_id}"""

    def test_update_work_item_success(self, client, created_work_item):
        """Update work item succeeds."""
        item_id = created_work_item["id"]
        update = {"priority": 5}

        response = client.put(f"/api/work-items/{item_id}", json=update)
        assert response.status_code == 200
        assert response.json()["priority"] == 5

    def test_update_work_item_status(self, client, created_work_item):
        """Update work item status."""
        item_id = created_work_item["id"]
        update = {"status": "in_progress"}

        response = client.put(f"/api/work-items/{item_id}", json=update)
        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"

    def test_update_work_item_completion_fields(self, client, created_work_item):
        """Update work item completion fields."""
        item_id = created_work_item["id"]
        update = {
            "status": "pr_ready",
            "branch_name": "feature/test-123",
            "commits_count": 3,
            "files_changed_count": 5,
            "pr_url": "https://github.com/org/repo/pull/123"
        }

        response = client.put(f"/api/work-items/{item_id}", json=update)
        assert response.status_code == 200
        data = response.json()
        assert data["branch_name"] == "feature/test-123"
        assert data["pr_url"] == "https://github.com/org/repo/pull/123"

    def test_update_work_item_not_found(self, client):
        """Update nonexistent work item returns 404."""
        fake_id = str(uuid4())
        response = client.put(f"/api/work-items/{fake_id}", json={"priority": 1})
        assert response.status_code == 404

    def test_update_work_item_reassign_team(self, client, created_work_item, sample_team_data):
        """Reassign work item to different team."""
        # Create new team
        new_team_data = {**sample_team_data, "name": "New Team"}
        new_team = client.post("/api/teams/", json=new_team_data).json()

        item_id = created_work_item["id"]
        update = {"team_id": new_team["id"]}

        response = client.put(f"/api/work-items/{item_id}", json=update)
        assert response.status_code == 200
        assert response.json()["team_id"] == new_team["id"]


class TestDeleteWorkItem:
    """Tests for DELETE /api/work-items/{work_item_id}"""

    def test_delete_work_item_success(self, client, created_work_item):
        """Delete work item succeeds."""
        item_id = created_work_item["id"]
        response = client.delete(f"/api/work-items/{item_id}")
        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(f"/api/work-items/{item_id}")
        assert get_response.status_code == 404

    def test_delete_work_item_not_found(self, client):
        """Delete nonexistent work item returns 404."""
        fake_id = str(uuid4())
        response = client.delete(f"/api/work-items/{fake_id}")
        assert response.status_code == 404


class TestBulkAssign:
    """Tests for POST /api/work-items/bulk-assign"""

    def test_bulk_assign_success(self, client, created_team, sample_work_item_data):
        """Bulk assign multiple work items to a team."""
        # Create work items without team
        item_ids = []
        for i in range(3):
            data = {**sample_work_item_data, "external_id": f"BULK-{i}"}
            response = client.post("/api/work-items/", json=data)
            item_ids.append(response.json()["id"])

        # Bulk assign
        response = client.post("/api/work-items/bulk-assign", json={
            "work_item_ids": item_ids,
            "team_id": created_team["id"]
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        for item in data:
            assert item["team_id"] == created_team["id"]

    def test_bulk_assign_team_not_found(self, client, sample_work_item_data):
        """Bulk assign to nonexistent team fails."""
        # Create a work item
        response = client.post("/api/work-items/", json=sample_work_item_data)
        item_id = response.json()["id"]

        # Try to assign to fake team
        response = client.post("/api/work-items/bulk-assign", json={
            "work_item_ids": [item_id],
            "team_id": str(uuid4())
        })
        assert response.status_code == 404

    def test_bulk_assign_item_not_found(self, client, created_team):
        """Bulk assign with nonexistent work item fails."""
        response = client.post("/api/work-items/bulk-assign", json={
            "work_item_ids": [str(uuid4())],
            "team_id": created_team["id"]
        })
        assert response.status_code == 404
