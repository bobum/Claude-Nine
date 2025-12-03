"""Run management routes for orchestrator session tracking"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
from uuid import UUID
import uuid
from datetime import datetime

from ..database import get_db
from ..models import Run, RunTask, Team, WorkItem
from ..schemas import (
    Run as RunSchema,
    RunCreate,
    RunTask as RunTaskSchema,
    RunWithTasks,
    RunStatus,
    RunTaskStatus,
)
from ..services.orchestrator_service import get_orchestrator_service

router = APIRouter(tags=["runs"])


@router.get("/", response_model=List[RunSchema])
def list_runs(
    team_id: UUID = None,
    status: RunStatus = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """List runs, optionally filtered by team or status"""
    query = db.query(Run)
    if team_id:
        query = query.filter(Run.team_id == team_id)
    if status:
        query = query.filter(Run.status == status)
    return query.order_by(desc(Run.created_at)).limit(limit).all()


@router.post("/", response_model=RunSchema)
def create_run(run_data: RunCreate, db: Session = Depends(get_db)):
    """Create a new run for a team with selected work items"""
    # Verify team exists
    team = db.query(Team).filter(Team.id == run_data.team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Create the run
    run = Run(
        id=uuid.uuid4(),
        team_id=run_data.team_id,
        session_id=run_data.session_id,
        status="pending",
        integration_branch=f"integration/{run_data.session_id}",
    )
    db.add(run)

    # Create run tasks for each selected work item
    for work_item_id in run_data.selected_work_item_ids:
        work_item = db.query(WorkItem).filter(WorkItem.id == work_item_id).first()
        if work_item:
            task = RunTask(
                id=uuid.uuid4(),
                run_id=run.id,
                work_item_id=work_item_id,
                status="pending",
            )
            db.add(task)

    db.commit()
    db.refresh(run)

    # Start the orchestrator for this run
    try:
        orchestrator_service = get_orchestrator_service()
        orchestrator_service.start_team(run_data.team_id, db, dry_run=run_data.dry_run)
    except Exception as e:
        # Log but don't fail - run is created, orchestrator can be started manually
        import logging
        logging.getLogger(__name__).error(f"Failed to start orchestrator: {e}")
    return run


@router.get("/{run_id}", response_model=RunWithTasks)
def get_run(run_id: UUID, db: Session = Depends(get_db)):
    """Get a run with all its tasks"""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.patch("/{run_id}/status")
def update_run_status(
    run_id: UUID,
    status: RunStatus,
    error_message: str = None,
    db: Session = Depends(get_db)
):
    """Update run status"""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    run.status = status.value
    if status == RunStatus.running and not run.started_at:
        run.started_at = datetime.utcnow()
    if status in [RunStatus.completed, RunStatus.failed, RunStatus.cancelled]:
        run.completed_at = datetime.utcnow()
    if error_message:
        run.error_message = error_message

    db.commit()
    db.refresh(run)
    return run


@router.patch("/{run_id}/tasks/{task_id}")
def update_task(
    run_id: UUID,
    task_id: UUID,
    status: RunTaskStatus = None,
    agent_name: str = None,
    branch_name: str = None,
    worktree_path: str = None,
    telemetry_data: dict = None,
    error_message: str = None,
    db: Session = Depends(get_db)
):
    """Update a run task with status/telemetry"""
    task = db.query(RunTask).filter(
        RunTask.id == task_id,
        RunTask.run_id == run_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if status:
        task.status = status.value
        if status == RunTaskStatus.running and not task.started_at:
            task.started_at = datetime.utcnow()
        if status in [RunTaskStatus.completed, RunTaskStatus.failed]:
            task.completed_at = datetime.utcnow()
    if agent_name:
        task.agent_name = agent_name
    if branch_name:
        task.branch_name = branch_name
    if worktree_path:
        task.worktree_path = worktree_path
    if telemetry_data:
        task.telemetry_data = telemetry_data
    if error_message:
        task.error_message = error_message

    db.commit()
    db.refresh(task)
    return task


@router.post("/{run_id}/cancel")
def cancel_run(run_id: UUID, db: Session = Depends(get_db)):
    """Cancel a running run"""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.status not in ["pending", "running", "merging"]:
        raise HTTPException(status_code=400, detail="Cannot cancel a completed run")

    run.status = "cancelled"
    run.completed_at = datetime.utcnow()

    # Cancel all pending tasks
    for task in run.tasks:
        if task.status in ["pending", "running"]:
            task.status = "failed"
            task.error_message = "Run cancelled"
            task.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(run)
    return run


@router.delete("/{run_id}")
def delete_run(run_id: UUID, db: Session = Depends(get_db)):
    """Delete a run and all its tasks"""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    db.delete(run)
    db.commit()
    return {"message": "Run deleted"}


@router.patch("/tasks/by-work-item/{work_item_id}")
def update_task_by_work_item(
    work_item_id: UUID,
    status: RunTaskStatus = None,
    agent_name: str = None,
    branch_name: str = None,
    worktree_path: str = None,
    error_message: str = None,
    db: Session = Depends(get_db)
):
    """
    Update a run task by work_item_id.
    
    This endpoint is used by the orchestrator subprocess to update task status
    and set agent_name without needing to know the run_id or task_id.
    Only updates tasks in active (pending/running) runs.
    """
    # Find the task by work_item_id in an active run
    task = db.query(RunTask).join(Run).filter(
        RunTask.work_item_id == work_item_id,
        Run.status.in_(["pending", "running", "merging"])
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=404, 
            detail=f"No active task found for work_item_id {work_item_id}"
        )

    if status:
        task.status = status.value
        if status == RunTaskStatus.running and not task.started_at:
            task.started_at = datetime.utcnow()
        if status in [RunTaskStatus.completed, RunTaskStatus.failed]:
            task.completed_at = datetime.utcnow()
    if agent_name:
        task.agent_name = agent_name
    if branch_name:
        task.branch_name = branch_name
    if worktree_path:
        task.worktree_path = worktree_path
    if error_message:
        task.error_message = error_message

    db.commit()
    db.refresh(task)
    return task
