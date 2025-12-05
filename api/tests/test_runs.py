"""
Tests for Runs API endpoints.

Covers:
- Run CRUD operations
- Run task updates
- Status transitions
- Run cancellation
"""

import pytest
from uuid import uuid4
from unittest.mock import patch, MagicMock


@pytest.fixture
def created_run(client, created_team, created_work_item):
    """Create a run with a task for testing."""
    # Mock the orchestrator service to avoid actually starting processes
    with patch("api.app.routes.runs.get_orchestrator_service") as mock_service:
        mock_service.return_value.start_team.return_value = {"status": "started"}

        run_data = {
            "team_id": created_team["id"],
            "session_id": "test123",
            "selected_work_item_ids": [created_work_item["id"]],
            "dry_run": True
        }
        response = client.post("/api/runs/", json=run_data)
        assert response.status_code == 200
        return response.json()


class TestListRuns:
    """Tests for GET /api/runs/"""

    def test_list_runs_empty(self, client):
        """List runs returns empty when none exist."""
        response = client.get("/api/runs/")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_runs_with_data(self, client, created_run):
        """List runs returns created runs."""
        response = client.get("/api/runs/")
        assert response.status_code == 200
        runs = response.json()
        assert len(runs) == 1
        assert runs[0]["session_id"] == "test123"

    def test_list_runs_filter_by_team(self, client, created_run):
        """List runs can filter by team_id."""
        team_id = created_run["team_id"]
        response = client.get(f"/api/runs/?team_id={team_id}")
        assert response.status_code == 200
        assert len(response.json()) == 1

        # Different team should return empty
        response = client.get(f"/api/runs/?team_id={uuid4()}")
        assert response.status_code == 200
        assert len(response.json()) == 0

    def test_list_runs_filter_by_status(self, client, created_run):
        """List runs can filter by status."""
        response = client.get("/api/runs/?status=pending")
        assert response.status_code == 200
        assert len(response.json()) == 1

        response = client.get("/api/runs/?status=completed")
        assert response.status_code == 200
        assert len(response.json()) == 0


class TestCreateRun:
    """Tests for POST /api/runs/"""

    def test_create_run_success(self, client, created_team, created_work_item):
        """Create run with valid data succeeds."""
        with patch("api.app.routes.runs.get_orchestrator_service") as mock_service:
            mock_service.return_value.start_team.return_value = {"status": "started"}

            run_data = {
                "team_id": created_team["id"],
                "session_id": "abc12345",
                "selected_work_item_ids": [created_work_item["id"]],
                "dry_run": True
            }
            response = client.post("/api/runs/", json=run_data)
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "abc12345"
            assert data["status"] == "pending"
            assert data["integration_branch"] == "integration/abc12345"
            assert len(data["tasks"]) == 1

    def test_create_run_team_not_found(self, client, created_work_item):
        """Create run for nonexistent team fails."""
        run_data = {
            "team_id": str(uuid4()),
            "session_id": "test123",
            "selected_work_item_ids": [created_work_item["id"]]
        }
        response = client.post("/api/runs/", json=run_data)
        assert response.status_code == 404

    def test_create_run_no_work_items(self, client, created_team):
        """Create run without work items creates run with no tasks."""
        with patch("api.app.routes.runs.get_orchestrator_service") as mock_service:
            mock_service.return_value.start_team.return_value = {"status": "started"}

            run_data = {
                "team_id": created_team["id"],
                "session_id": "empty123",
                "selected_work_item_ids": []
            }
            response = client.post("/api/runs/", json=run_data)
            assert response.status_code == 200
            assert len(response.json()["tasks"]) == 0


class TestGetRun:
    """Tests for GET /api/runs/{run_id}"""

    def test_get_run_success(self, client, created_run):
        """Get run by ID returns run with tasks."""
        run_id = created_run["id"]
        response = client.get(f"/api/runs/{run_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == run_id
        assert "tasks" in data

    def test_get_run_not_found(self, client):
        """Get nonexistent run returns 404."""
        fake_id = str(uuid4())
        response = client.get(f"/api/runs/{fake_id}")
        assert response.status_code == 404


class TestUpdateRunStatus:
    """Tests for PATCH /api/runs/{run_id}/status"""

    def test_update_run_status_to_running(self, client, created_run):
        """Update run status to running sets started_at."""
        run_id = created_run["id"]
        response = client.patch(f"/api/runs/{run_id}/status?status=running")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["started_at"] is not None

    def test_update_run_status_to_completed(self, client, created_run):
        """Update run status to completed sets completed_at."""
        run_id = created_run["id"]
        response = client.patch(f"/api/runs/{run_id}/status?status=completed")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["completed_at"] is not None

    def test_update_run_status_with_error(self, client, created_run):
        """Update run status to failed with error message."""
        run_id = created_run["id"]
        response = client.patch(
            f"/api/runs/{run_id}/status?status=failed&error_message=Something+went+wrong"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_message"] == "Something went wrong"

    def test_update_run_status_not_found(self, client):
        """Update status of nonexistent run returns 404."""
        fake_id = str(uuid4())
        response = client.patch(f"/api/runs/{fake_id}/status?status=running")
        assert response.status_code == 404


class TestUpdateTask:
    """Tests for PATCH /api/runs/{run_id}/tasks/{task_id}"""

    def test_update_task_status(self, client, created_run):
        """Update task status."""
        run_id = created_run["id"]
        task_id = created_run["tasks"][0]["id"]

        response = client.patch(
            f"/api/runs/{run_id}/tasks/{task_id}?status=running"
        )
        assert response.status_code == 200
        assert response.json()["status"] == "running"

    def test_update_task_agent_name(self, client, created_run):
        """Update task agent name."""
        run_id = created_run["id"]
        task_id = created_run["tasks"][0]["id"]

        response = client.patch(
            f"/api/runs/{run_id}/tasks/{task_id}?agent_name=DevAgent1"
        )
        assert response.status_code == 200
        assert response.json()["agent_name"] == "DevAgent1"

    def test_update_task_branch_info(self, client, created_run):
        """Update task with branch and worktree info."""
        run_id = created_run["id"]
        task_id = created_run["tasks"][0]["id"]

        response = client.patch(
            f"/api/runs/{run_id}/tasks/{task_id}"
            "?branch_name=feature/test-123"
            "&worktree_path=/tmp/.agent-workspace/worktree-test"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["branch_name"] == "feature/test-123"
        assert data["worktree_path"] == "/tmp/.agent-workspace/worktree-test"

    def test_update_task_not_found(self, client, created_run):
        """Update nonexistent task returns 404."""
        run_id = created_run["id"]
        fake_task_id = str(uuid4())

        response = client.patch(
            f"/api/runs/{run_id}/tasks/{fake_task_id}?status=running"
        )
        assert response.status_code == 404


class TestCancelRun:
    """Tests for POST /api/runs/{run_id}/cancel"""

    def test_cancel_pending_run(self, client, created_run):
        """Cancel a pending run."""
        run_id = created_run["id"]
        response = client.post(f"/api/runs/{run_id}/cancel")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["completed_at"] is not None

        # Verify tasks are marked as failed via GET endpoint
        get_response = client.get(f"/api/runs/{run_id}")
        run_data = get_response.json()
        for task in run_data["tasks"]:
            assert task["status"] == "failed"
            assert task["error_message"] == "Run cancelled"

    def test_cancel_running_run(self, client, created_run):
        """Cancel a running run."""
        run_id = created_run["id"]
        # First set to running
        client.patch(f"/api/runs/{run_id}/status?status=running")

        response = client.post(f"/api/runs/{run_id}/cancel")
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_cancel_completed_run_fails(self, client, created_run):
        """Cannot cancel a completed run."""
        run_id = created_run["id"]
        # Mark as completed
        client.patch(f"/api/runs/{run_id}/status?status=completed")

        response = client.post(f"/api/runs/{run_id}/cancel")
        assert response.status_code == 400

    def test_cancel_run_not_found(self, client):
        """Cancel nonexistent run returns 404."""
        fake_id = str(uuid4())
        response = client.post(f"/api/runs/{fake_id}/cancel")
        assert response.status_code == 404


class TestDeleteRun:
    """Tests for DELETE /api/runs/{run_id}"""

    def test_delete_run_success(self, client, created_run):
        """Delete run and its tasks."""
        run_id = created_run["id"]
        response = client.delete(f"/api/runs/{run_id}")
        assert response.status_code == 200

        # Verify deleted
        get_response = client.get(f"/api/runs/{run_id}")
        assert get_response.status_code == 404

    def test_delete_run_not_found(self, client):
        """Delete nonexistent run returns 404."""
        fake_id = str(uuid4())
        response = client.delete(f"/api/runs/{fake_id}")
        assert response.status_code == 404


class TestUpdateTaskByWorkItem:
    """Tests for PATCH /api/runs/tasks/by-work-item/{work_item_id}"""

    def test_update_task_by_work_item(self, client, created_run, created_work_item):
        """Update task by work item ID."""
        work_item_id = created_work_item["id"]

        response = client.patch(
            f"/api/runs/tasks/by-work-item/{work_item_id}"
            "?status=running&agent_name=TestAgent"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["agent_name"] == "TestAgent"

    def test_update_task_by_work_item_not_found(self, client):
        """Update task for nonexistent work item returns 404."""
        fake_id = str(uuid4())
        response = client.patch(
            f"/api/runs/tasks/by-work-item/{fake_id}?status=running"
        )
        assert response.status_code == 404
