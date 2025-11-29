"""
Orchestrator Service - Manages team execution and agent orchestration

This service acts as the bridge between the FastAPI backend and the CrewAI orchestrator.
It handles spawning orchestrator processes, tracking their status, and syncing back to the database.
"""

import os
import sys
import subprocess
import threading
import json
import tempfile
import logging
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session
import asyncio


from ..models import Team, WorkItem
from ..database import SessionLocal
from ..websocket import notify_work_item_update, notify_team_update
from ..config import settings

logger = logging.getLogger(__name__)


class OrchestratorService:
    """
    Manages orchestrator instances for teams.

    Each team gets its own orchestrator process that runs in the background.
    The service tracks running orchestrators and provides status updates.
    """

    def __init__(self):
        # Track running orchestrators: team_id -> subprocess info
        self.running_orchestrators: Dict[str, dict] = {}
        self._lock = threading.Lock()

        # Path to the orchestrator script
        self.orchestrator_script = self._find_orchestrator_script()

    def _find_orchestrator_script(self) -> Path:
        """Find the orchestrator.py script in the project"""
        # Try to find the orchestrator relative to the API directory
        api_dir = Path(__file__).parent.parent.parent
        orchestrator_dir = api_dir.parent / "claude-multi-agent-orchestrator"
        orchestrator_script = orchestrator_dir / "orchestrator.py"

        if not orchestrator_script.exists():
            raise FileNotFoundError(
                f"Orchestrator script not found at {orchestrator_script}. "
                "Please ensure claude-multi-agent-orchestrator directory exists."
            )

        return orchestrator_script

    def start_team(self, team_id: UUID, db: Session) -> dict:
        """
        Start orchestrator for a team

        Args:
            team_id: UUID of the team to start
            db: Database session

        Returns:
            dict with status information
        """
        print(f"=== DEBUG: start_team called for team {team_id} ===")
        team_id_str = str(team_id)

        # Check if already running
        with self._lock:
            if team_id_str in self.running_orchestrators:
                return {
                    "status": "already_running",
                    "message": "Team orchestrator is already running"
                }

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

        # Generate YAML configuration for the orchestrator
        tasks_yaml = self._generate_tasks_yaml(team, work_items, db)
        config_yaml = self._generate_config_yaml(team)

        # Create temporary files for the configuration
        # Use manual file writing with explicit UTF-8 to avoid Windows encoding issues
        import tempfile as _tempfile
        temp_dir = _tempfile.gettempdir()

        tasks_file_path = Path(temp_dir) / f'team_{team_id_str}_tasks_{os.urandom(4).hex()}.yaml'
        with open(tasks_file_path, 'w', encoding='utf-8') as f:
            f.write(tasks_yaml)

        config_file_path = Path(temp_dir) / f'team_{team_id_str}_config_{os.urandom(4).hex()}.yaml'
        with open(config_file_path, 'w', encoding='utf-8') as f:
            f.write(config_yaml)

        # Log the generated configuration
        print(f"=== DEBUG: Generated config YAML for team {team_id_str} ===")
        print(config_yaml)
        print(f"=== DEBUG: Config file written to: {config_file_path} ===")
        print(f"=== DEBUG: Generated tasks YAML for team {team_id_str} ===")
        print(tasks_yaml)
        print(f"=== DEBUG: Tasks file written to: {tasks_file_path} ===")
        logger.info(f"Generated config YAML for team {team_id_str}:\n{config_yaml}")
        logger.info(f"Config file written to: {config_file_path}")
        logger.info(f"Generated tasks YAML for team {team_id_str}:\n{tasks_yaml}")
        logger.info(f"Tasks file written to: {tasks_file_path}")

        # Prepare the command to run the orchestrator
        # Use the venv Python interpreter explicitly (not sys.executable which may be system Python)
        venv_python = Path(__file__).parent.parent.parent.parent / "venv" / "Scripts" / "python.exe"
        if not venv_python.exists():
            # Fallback for Linux/Mac
            venv_python = Path(__file__).parent.parent.parent.parent / "venv" / "bin" / "python"

        cmd = [
            str(venv_python),
            str(self.orchestrator_script),
            '--config', str(config_file_path),
            '--tasks', str(tasks_file_path),
            '--team-id', team_id_str  # Pass team ID so orchestrator can report back
        ]

        # Set environment variables
        env = os.environ.copy()
        env['ANTHROPIC_API_KEY'] = settings.anthropic_api_key
        env['CLAUDE_NINE_API_URL'] = 'http://localhost:8000'

        # Log the command
        logger.info(f"Starting orchestrator for team {team_id_str}")
        logger.info(f"Command: {' '.join(cmd)}")
        logger.info(f"Working directory: {team.repo_path}")
        logger.info(f"Python executable: {sys.executable}")

        # Start the orchestrator process
        try:
            process = subprocess.Popen(
                cmd,
                cwd=team.repo_path,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Track the running orchestrator
            with self._lock:
                self.running_orchestrators[team_id_str] = {
                    'process': process,
                    'tasks_file': str(tasks_file_path),
                    'config_file': str(config_file_path),
                    'started_at': datetime.utcnow(),
                    'work_items': [str(wi.id) for wi in work_items]
                }

            # Start a background thread to monitor the process
            monitor_thread = threading.Thread(
                target=self._monitor_orchestrator,
                args=(team_id_str, process, db),
                daemon=True
            )
            monitor_thread.start()

            # Update work items to in_progress
            for work_item in work_items:
                work_item.status = "in_progress"
                work_item.started_at = datetime.utcnow()
                # Send WebSocket notification
                try:
                    asyncio.run(notify_work_item_update(
                        str(work_item.id),
                        str(team_id),
                        "status_changed",
                        {"status": "in_progress", "started_at": work_item.started_at.isoformat()}
                    ))
                except RuntimeError:
                    pass  # Event loop may already be running

            db.commit()

            # Send team update notification
            try:
                asyncio.run(notify_team_update(
                    str(team_id),
                    "orchestrator_started",
                    {"message": f"Orchestrator started with {len(work_items)} work items"}
                ))
            except RuntimeError:
                pass  # Event loop may already be running

            return {
                "status": "started",
                "message": f"Orchestrator started for team {team.name}",
                "work_items_count": len(work_items)
            }

        except Exception as e:
            # Clean up temp files on error
            if tasks_file_path.exists():
                os.unlink(tasks_file_path)
            if config_file_path.exists():
                os.unlink(config_file_path)
            raise RuntimeError(f"Failed to start orchestrator: {str(e)}")

    def stop_team(self, team_id: UUID, db: Session) -> dict:
        """Stop orchestrator for a team"""
        team_id_str = str(team_id)

        with self._lock:
            if team_id_str not in self.running_orchestrators:
                return {
                    "status": "not_running",
                    "message": "Team orchestrator is not running"
                }

            orch_info = self.running_orchestrators[team_id_str]
            process = orch_info['process']

            # Terminate the process
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

            # Clean up temp files
            if os.path.exists(orch_info['tasks_file']):
                os.unlink(orch_info['tasks_file'])
            if os.path.exists(orch_info['config_file']):
                os.unlink(orch_info['config_file'])

            # Remove from tracking
            del self.running_orchestrators[team_id_str]

        # Update database status
        team = db.query(Team).filter(Team.id == team_id).first()
        if team:
            team.status = "stopped"
            db.commit()

        return {
            "status": "stopped",
            "message": "Orchestrator stopped successfully"
        }

    def get_status(self, team_id: UUID) -> dict:
        """Get status of team orchestrator"""
        team_id_str = str(team_id)

        with self._lock:
            if team_id_str not in self.running_orchestrators:
                return {
                    "running": False,
                    "message": "Orchestrator not running"
                }

            orch_info = self.running_orchestrators[team_id_str]
            process = orch_info['process']

            return {
                "running": True,
                "pid": process.pid,
                "started_at": orch_info['started_at'].isoformat(),
                "work_items": orch_info['work_items']
            }

    def _monitor_orchestrator(self, team_id_str: str, process: subprocess.Popen, db_session_maker):
        """Monitor orchestrator process and update database when it completes"""
        # Wait for process to complete
        stdout, stderr = process.communicate()

        # Log the output
        logger.info(f"Orchestrator for team {team_id_str} finished with return code: {process.returncode}")
        if stdout:
            logger.info(f"Orchestrator stdout:\n{stdout}")
        if stderr:
            logger.error(f"Orchestrator stderr:\n{stderr}")

        # Process has finished
        with self._lock:
            if team_id_str in self.running_orchestrators:
                orch_info = self.running_orchestrators[team_id_str]

                # Clean up temp files
                if os.path.exists(orch_info['tasks_file']):
                    os.unlink(orch_info['tasks_file'])
                if os.path.exists(orch_info['config_file']):
                    os.unlink(orch_info['config_file'])

                del self.running_orchestrators[team_id_str]

        # Update database
        db = SessionLocal()
        try:
            team = db.query(Team).filter(Team.id == UUID(team_id_str)).first()
            if team:
                team.status = "stopped"

                # Update work items based on process result
                if process.returncode == 0:
                    # Success - mark as completed
                    work_items = db.query(WorkItem).filter(
                        WorkItem.team_id == UUID(team_id_str),
                        WorkItem.status == "in_progress"
                    ).all()
                    for work_item in work_items:
                        work_item.status = "completed"
                        work_item.completed_at = datetime.utcnow()
                        # Send WebSocket notification
                        try:
                            asyncio.run(notify_work_item_update(
                                str(work_item.id),
                                team_id_str,
                                "status_changed",
                                {"status": "completed", "completed_at": work_item.completed_at.isoformat()}
                            ))
                        except RuntimeError:
                            pass  # Event loop may already be running
                else:
                    # Error - mark as queued again
                    work_items = db.query(WorkItem).filter(
                        WorkItem.team_id == UUID(team_id_str),
                        WorkItem.status == "in_progress"
                    ).all()
                    for work_item in work_items:
                        work_item.status = "queued"
                        work_item.started_at = None
                        # Send WebSocket notification
                        try:
                            asyncio.run(notify_work_item_update(
                                str(work_item.id),
                                team_id_str,
                                "status_changed",
                                {"status": "queued", "error": "Orchestrator failed"}
                            ))
                        except RuntimeError:
                            pass  # Event loop may already be running

                db.commit()

                # Send team update notification
                status_msg = "completed successfully" if process.returncode == 0 else "failed"
                try:
                    asyncio.run(notify_team_update(
                        team_id_str,
                        "orchestrator_stopped",
                        {"message": f"Orchestrator {status_msg}", "return_code": process.returncode}
                    ))
                except RuntimeError:
                    pass  # Event loop may already be running
        finally:
            db.close()

    def _generate_tasks_yaml(self, team: Team, work_items: List[WorkItem], db: Session) -> str:
        """Generate YAML tasks configuration from database work items.

        Each work item becomes a feature task. The orchestrator will create
        one agent per task dynamically - no pre-existing agents required.
        """
        yaml_content = "# Auto-generated tasks from database\n"
        yaml_content += f"# Team: {team.name}\n"
        yaml_content += f"# Work items: {len(work_items)}\n\n"
        yaml_content += "features:\n"

        for work_item in work_items:
            # Create a safe branch name from the work item external_id
            external_id = work_item.external_id or str(work_item.id)[:8]
            branch_name = f"feature/{external_id}".lower().replace(" ", "-")

            # Create a safe name for the feature (used as agent name)
            feature_name = external_id.replace("-", "_").replace(" ", "_").lower()

            yaml_content += f"  - name: {feature_name}\n"
            yaml_content += f"    branch: {branch_name}\n"
            yaml_content += f"    work_item_id: {external_id}\n"
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

    def _generate_config_yaml(self, team: Team) -> str:
        """Generate config.yaml for the orchestrator"""
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


# Global singleton instance
_orchestrator_service: Optional[OrchestratorService] = None

def get_orchestrator_service() -> OrchestratorService:
    """Get the global orchestrator service instance"""
    global _orchestrator_service
    if _orchestrator_service is None:
        _orchestrator_service = OrchestratorService()
    return _orchestrator_service
