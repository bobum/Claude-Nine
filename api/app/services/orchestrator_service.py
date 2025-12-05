"""
Orchestrator Service - Manages team execution via Celery task queue.

This service decouples the API from the orchestrator by using Celery tasks.
Instead of spawning subprocesses directly, it enqueues tasks to Redis
which are consumed by separate Celery worker processes.
"""

import logging
import threading
from typing import Dict, Optional
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session
import asyncio
from celery.result import AsyncResult

from ..models import Team, WorkItem, Run
from ..websocket import notify_work_item_update, notify_team_update
from ..config import settings
from ..celery_app import celery_app
from ..tasks.orchestrator_tasks import run_orchestrator

logger = logging.getLogger(__name__)


def run_async_notification(coro):
    """
    Run an async notification coroutine from sync code.

    Handles both cases:
    - When called from a thread with no event loop: creates a new loop
    - When called from within an existing event loop: schedules the task
    """
    try:
        loop = asyncio.get_running_loop()
        asyncio.ensure_future(coro, loop=loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(coro)
        finally:
            loop.close()


class OrchestratorService:
    """
    Manages orchestrator execution via Celery task queue.

    Instead of spawning subprocesses directly, this service enqueues tasks
    to a Redis-backed Celery queue. Separate worker processes consume the
    tasks and execute the orchestrator logic.

    Benefits:
    - Decoupled: API does not manage long-running processes
    - Scalable: Multiple workers can process tasks in parallel
    - Resilient: Tasks persist in Redis if API restarts
    - Secure: No subprocess/command injection risks
    """

    def __init__(self):
        # Track running tasks: team_id -> task info
        self.running_tasks: Dict[str, dict] = {}
        self._lock = threading.Lock()

    def start_team(self, team_id: UUID, db: Session, dry_run: bool = False) -> dict:
        """
        Start orchestrator for a team by enqueuing a Celery task.

        Args:
            team_id: UUID of the team to start
            db: Database session
            dry_run: If True, use mock LLM responses (no API credits consumed)

        Returns:
            dict with status information including the Celery task ID
        """
        # Force dry-run if configured at API level
        if settings.force_dry_run:
            dry_run = True
            logger.info("FORCE_DRY_RUN is enabled - orchestrator will use mock LLM")

        team_id_str = str(team_id)
        logger.info(f"Enqueuing orchestrator task for team {team_id}, dry_run={dry_run}")

        # Check if already running
        with self._lock:
            if team_id_str in self.running_tasks:
                task_info = self.running_tasks[team_id_str]
                task_result = AsyncResult(task_info["task_id"], app=celery_app)

                # Check if the task is still actually running
                if task_result.state in ("PENDING", "STARTED", "RETRY"):
                    return {
                        "status": "already_running",
                        "message": "Team orchestrator is already running",
                        "task_id": task_info["task_id"]
                    }
                else:
                    # Task finished but was not cleaned up - remove it
                    del self.running_tasks[team_id_str]

        # Load team data
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise ValueError(f"Team {team_id} not found")

        # Load queued work items
        work_items = db.query(WorkItem).filter(
            WorkItem.team_id == team_id,
            WorkItem.status == "queued"
        ).all()

        if not work_items:
            raise ValueError("No work items in queue")

        # Find or create a Run record
        active_run = db.query(Run).filter(
            Run.team_id == team_id,
            Run.status == "pending"
        ).first()

        run_id = str(active_run.id) if active_run else None

        # Enqueue the Celery task
        work_item_ids = [str(wi.id) for wi in work_items]

        task = run_orchestrator.apply_async(
            kwargs={
                "team_id": team_id_str,
                "work_item_ids": work_item_ids,
                "dry_run": dry_run,
                "run_id": run_id
            },
            task_id=f"orchestrator-{team_id_str}-{datetime.utcnow().timestamp()}"
        )

        logger.info(f"Enqueued Celery task {task.id} for team {team_id_str}")

        # Track the task
        with self._lock:
            self.running_tasks[team_id_str] = {
                "task_id": task.id,
                "started_at": datetime.utcnow(),
                "work_items": work_item_ids
            }

        # Update Run status to indicate task is queued
        if active_run:
            active_run.status = "running"
            active_run.started_at = datetime.utcnow()
            logger.info(f"Updated Run {active_run.id} status to running")

        # Update work items to in_progress
        for work_item in work_items:
            work_item.status = "in_progress"
            work_item.started_at = datetime.utcnow()
            run_async_notification(notify_work_item_update(
                str(work_item.id),
                str(team_id),
                "status_changed",
                {
                    "id": str(work_item.id),
                    "status": "in_progress",
                    "started_at": work_item.started_at.isoformat(),
                    "title": work_item.title,
                    "external_id": work_item.external_id,
                }
            ))

        # Update team status
        team.status = "active"
        db.commit()

        # Send team update notification
        run_async_notification(notify_team_update(
            str(team_id),
            "orchestrator_started",
            {
                "message": f"Orchestrator task enqueued with {len(work_items)} work items",
                "task_id": task.id
            }
        ))

        return {
            "status": "started",
            "message": f"Orchestrator task enqueued for team {team.name}",
            "work_items_count": len(work_items),
            "task_id": task.id
        }

    def stop_team(self, team_id: UUID, db: Session) -> dict:
        """Stop orchestrator task for a team by revoking the Celery task."""
        team_id_str = str(team_id)

        with self._lock:
            if team_id_str not in self.running_tasks:
                return {
                    "status": "not_running",
                    "message": "Team orchestrator is not running"
                }

            task_info = self.running_tasks[team_id_str]
            task_id = task_info["task_id"]

            # Revoke the Celery task (terminate if already running)
            celery_app.control.revoke(task_id, terminate=True)
            logger.info(f"Revoked Celery task {task_id}")

            # Remove from tracking
            del self.running_tasks[team_id_str]

        # Update database status
        team = db.query(Team).filter(Team.id == team_id).first()
        if team:
            team.status = "stopped"

        # Update any running Run record
        active_run = db.query(Run).filter(
            Run.team_id == team_id,
            Run.status == "running"
        ).first()
        if active_run:
            active_run.status = "cancelled"
            active_run.completed_at = datetime.utcnow()

        # Reset work items to queued
        work_items = db.query(WorkItem).filter(
            WorkItem.team_id == team_id,
            WorkItem.status == "in_progress"
        ).all()
        for work_item in work_items:
            work_item.status = "queued"
            work_item.started_at = None
            run_async_notification(notify_work_item_update(
                str(work_item.id),
                team_id_str,
                "status_changed",
                {
                    "id": str(work_item.id),
                    "status": "queued",
                    "message": "Task cancelled",
                    "title": work_item.title,
                    "external_id": work_item.external_id,
                }
            ))

        db.commit()

        # Send notification
        run_async_notification(notify_team_update(
            team_id_str,
            "orchestrator_stopped",
            {"message": "Orchestrator task cancelled"}
        ))

        return {
            "status": "stopped",
            "message": "Orchestrator task cancelled successfully"
        }

    def get_status(self, team_id: UUID) -> dict:
        """Get status of team orchestrator task."""
        team_id_str = str(team_id)

        with self._lock:
            if team_id_str not in self.running_tasks:
                return {
                    "running": False,
                    "message": "Orchestrator not running"
                }

            task_info = self.running_tasks[team_id_str]
            task_id = task_info["task_id"]

            # Get Celery task state
            task_result = AsyncResult(task_id, app=celery_app)

            # Map Celery states to our status
            state = task_result.state
            if state == "PENDING":
                status_message = "Task queued, waiting for worker"
            elif state == "STARTED":
                status_message = "Task is executing"
            elif state == "SUCCESS":
                status_message = "Task completed successfully"
                # Clean up tracking
                del self.running_tasks[team_id_str]
                return {
                    "running": False,
                    "message": status_message,
                    "result": task_result.result
                }
            elif state == "FAILURE":
                status_message = f"Task failed: {task_result.result}"
                del self.running_tasks[team_id_str]
                return {
                    "running": False,
                    "message": status_message,
                    "error": str(task_result.result)
                }
            elif state == "REVOKED":
                status_message = "Task was cancelled"
                del self.running_tasks[team_id_str]
                return {
                    "running": False,
                    "message": status_message
                }
            else:
                status_message = f"Task state: {state}"

            return {
                "running": True,
                "task_id": task_id,
                "state": state,
                "started_at": task_info["started_at"].isoformat(),
                "work_items": task_info["work_items"],
                "message": status_message
            }

    def get_task_result(self, task_id: str) -> dict:
        """Get the result of a specific Celery task."""
        task_result = AsyncResult(task_id, app=celery_app)

        return {
            "task_id": task_id,
            "state": task_result.state,
            "ready": task_result.ready(),
            "successful": task_result.successful() if task_result.ready() else None,
            "result": task_result.result if task_result.ready() else None
        }


# Global singleton instance
_orchestrator_service: Optional[OrchestratorService] = None


def get_orchestrator_service() -> OrchestratorService:
    """Get the global orchestrator service instance"""
    global _orchestrator_service
    if _orchestrator_service is None:
        _orchestrator_service = OrchestratorService()
    return _orchestrator_service
