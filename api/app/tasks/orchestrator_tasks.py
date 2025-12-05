"""
Celery tasks for orchestrator execution.

This module contains the Celery task that executes the orchestrator subprocess.
The task is decoupled from the API - it runs in a separate worker process.
"""

import os
import subprocess
import logging
import tempfile
from pathlib import Path
from datetime import datetime
from uuid import UUID
from typing import Optional

from celery import Task
from celery.exceptions import Reject

from ..celery_app import celery_app
from ..database import SessionLocal
from ..models import Team, WorkItem, Run, RunTask
from ..config import settings

logger = logging.getLogger(__name__)


def _find_orchestrator_script() -> Path:
    """Find the orchestrator.py script in the project."""
    api_dir = Path(__file__).parent.parent.parent
    orchestrator_dir = api_dir.parent / "claude-multi-agent-orchestrator"
    orchestrator_script = orchestrator_dir / "orchestrator.py"

    if not orchestrator_script.exists():
        raise FileNotFoundError(
            f"Orchestrator script not found at {orchestrator_script}. "
            "Please ensure claude-multi-agent-orchestrator directory exists."
        )

    return orchestrator_script


def _get_python_executable() -> Path:
    """Get the Python executable from the virtual environment."""
    venv_python = Path(__file__).parent.parent.parent.parent / "venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        # Fallback for Linux/Mac
        venv_python = Path(__file__).parent.parent.parent.parent / "venv" / "bin" / "python"
    return venv_python


def _generate_tasks_yaml(team: Team, work_items: list[WorkItem]) -> str:
    """Generate YAML tasks configuration from database work items."""
    yaml_content = "# Auto-generated tasks from database\n"
    yaml_content += f"# Team: {team.name}\n"
    yaml_content += f"# Work items: {len(work_items)}\n\n"
    yaml_content += "features:\n"

    for work_item in work_items:
        external_id = work_item.external_id or str(work_item.id)[:8]
        branch_name = f"feature/{external_id}".lower().replace(" ", "-")
        feature_name = external_id.replace("-", "_").replace(" ", "_").lower()

        yaml_content += f"  - name: {feature_name}\n"
        yaml_content += f"    branch: {branch_name}\n"
        yaml_content += f"    work_item_id: {str(work_item.id)}\n"
        yaml_content += f"    external_id: {external_id}\n"
        yaml_content += f"    role: Software Developer\n"
        yaml_content += f"    goal: {work_item.title}\n"
        yaml_content += f"    description: |\n"
        yaml_content += f"      Task: {work_item.title}\n"
        yaml_content += f"      \n"
        if work_item.description:
            for line in work_item.description.split('\n'):
                yaml_content += f"      {line}\n"
        if work_item.acceptance_criteria:
            yaml_content += f"      \n"
            yaml_content += f"      Acceptance Criteria:\n"
            for line in work_item.acceptance_criteria.split('\n'):
                yaml_content += f"      {line}\n"
        yaml_content += f"    expected_output: |\n"
        yaml_content += f"      Complete implementation of: {work_item.title}\n"
        yaml_content += f"      All code committed to branch {branch_name}\n"
        yaml_content += f"      Ready for merge to {team.main_branch or 'main'}\n"
        yaml_content += "\n"

    return yaml_content


def _generate_config_yaml(team: Team) -> str:
    """Generate config.yaml for the orchestrator."""
    yaml_content = f"# Auto-generated config for team: {team.name}\n\n"
    yaml_content += "# API Keys\n"
    yaml_content += f"anthropic_api_key: {settings.anthropic_api_key}\n"
    yaml_content += "\n"
    yaml_content += "# CrewAI Configuration\n"
    yaml_content += "crew:\n"
    yaml_content += "  process: parallel\n"
    yaml_content += "  verbose: true\n"
    yaml_content += "\n"
    yaml_content += "# Git Configuration\n"
    yaml_content += "git:\n"
    yaml_content += f"  main_branch: {team.main_branch or 'main'}\n"
    yaml_content += "  auto_merge: false\n"
    yaml_content += "\n"
    yaml_content += "# Monitor Configuration\n"
    yaml_content += "monitor:\n"
    yaml_content += "  enabled: true\n"
    yaml_content += "  check_interval: 30\n"
    yaml_content += "\n"

    return yaml_content


class OrchestratorTask(Task):
    """Base task class with database session management."""

    _db = None

    @property
    def db(self):
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """Clean up database session after task completion."""
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task(
    bind=True,
    base=OrchestratorTask,
    name="app.tasks.orchestrator_tasks.run_orchestrator",
    max_retries=1,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def run_orchestrator(
    self,
    team_id: str,
    work_item_ids: list[str],
    dry_run: bool = False,
    run_id: Optional[str] = None,
) -> dict:
    """
    Execute the orchestrator for a team's work items.

    This task runs in a Celery worker process, completely decoupled from the API.

    Args:
        team_id: UUID of the team
        work_item_ids: List of work item UUIDs to process
        dry_run: If True, use mock LLM responses (no API credits)
        run_id: Optional Run record ID for tracking

    Returns:
        dict with execution results
    """
    logger.info(f"Starting orchestrator task for team {team_id}")
    logger.info(f"Work items: {work_item_ids}, dry_run: {dry_run}")

    db = self.db
    team_uuid = UUID(team_id)

    # Load team
    team = db.query(Team).filter(Team.id == team_uuid).first()
    if not team:
        raise Reject(f"Team {team_id} not found", requeue=False)

    # Load work items
    work_items = db.query(WorkItem).filter(
        WorkItem.id.in_([UUID(wid) for wid in work_item_ids])
    ).all()

    if not work_items:
        raise Reject("No work items found", requeue=False)

    # Update Run status if provided
    run = None
    if run_id:
        run = db.query(Run).filter(Run.id == UUID(run_id)).first()
        if run:
            run.status = "running"
            run.started_at = datetime.utcnow()
            db.commit()

    # Update work items to in_progress
    for work_item in work_items:
        work_item.status = "in_progress"
        work_item.started_at = datetime.utcnow()
    db.commit()

    # Generate configuration files
    tasks_yaml = _generate_tasks_yaml(team, work_items)
    config_yaml = _generate_config_yaml(team)

    # Create temporary files
    temp_dir = tempfile.gettempdir()
    tasks_file = Path(temp_dir) / f'team_{team_id}_tasks_{os.urandom(4).hex()}.yaml'
    config_file = Path(temp_dir) / f'team_{team_id}_config_{os.urandom(4).hex()}.yaml'

    try:
        # Write config files
        tasks_file.write_text(tasks_yaml, encoding='utf-8')
        config_file.write_text(config_yaml, encoding='utf-8')

        logger.info(f"Config files written: {tasks_file}, {config_file}")

        # Build command
        orchestrator_script = _find_orchestrator_script()
        python_exe = _get_python_executable()

        cmd = [
            str(python_exe),
            str(orchestrator_script),
            '--config', str(config_file),
            '--tasks', str(tasks_file),
            '--team-id', team_id
        ]

        if dry_run or settings.force_dry_run:
            cmd.append('--dry-run')
            logger.info("DRY RUN MODE: Orchestrator will use mock LLM responses")

        # Set environment
        env = os.environ.copy()
        env['ANTHROPIC_API_KEY'] = settings.anthropic_api_key
        env['CLAUDE_NINE_API_URL'] = f'http://localhost:{settings.api_port}'

        logger.info(f"Executing: {' '.join(cmd)}")
        logger.info(f"Working directory: {team.repo_path}")

        # Run orchestrator subprocess
        process = subprocess.Popen(
            cmd,
            cwd=team.repo_path,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait for completion
        stdout, stderr = process.communicate()

        logger.info(f"Orchestrator completed with return code: {process.returncode}")
        if stdout:
            logger.info(f"Stdout:\n{stdout}")
        if stderr:
            logger.error(f"Stderr:\n{stderr}")

        # Update database based on result
        if process.returncode == 0:
            # Success
            for work_item in work_items:
                work_item.status = "completed"
                work_item.completed_at = datetime.utcnow()

            if run:
                run.status = "completed"
                run.completed_at = datetime.utcnow()

            result = {
                "status": "completed",
                "return_code": process.returncode,
                "message": "Orchestrator completed successfully"
            }
        else:
            # Failure - requeue work items
            for work_item in work_items:
                work_item.status = "queued"
                work_item.started_at = None

            if run:
                run.status = "failed"
                run.completed_at = datetime.utcnow()
                run.error_message = stderr[:500] if stderr else "Orchestrator failed"

            result = {
                "status": "failed",
                "return_code": process.returncode,
                "message": stderr[:500] if stderr else "Orchestrator failed",
            }

        # Update team status
        team.status = "stopped"
        db.commit()

        return result

    finally:
        # Clean up temp files
        if tasks_file.exists():
            os.unlink(tasks_file)
        if config_file.exists():
            os.unlink(config_file)
