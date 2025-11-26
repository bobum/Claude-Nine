#!/usr/bin/env python3
"""
Simplified Multi-Agent Orchestrator using Anthropic SDK directly.

This orchestrator manages Claude agents working on git branches.
Compatible with Python 3.14+.
"""

import os
import sys
import yaml
import logging
import argparse
from pathlib import Path
from datetime import datetime
from anthropic import Anthropic
from git_operations import GitOperations

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


class SimpleOrchestrator:
    """Simplified orchestrator using Anthropic SDK directly."""

    def __init__(self, config_path: str, tasks_path: str, team_id: str):
        """Initialize the orchestrator."""
        self.config = self._load_yaml(config_path)
        self.tasks_config = self._load_yaml(tasks_path)
        self.team_id = team_id
        self.repo_path = os.getcwd()

        # Initialize Anthropic client
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        self.client = Anthropic(api_key=api_key)

        # Git operations
        self.git_ops = GitOperations(self.repo_path)

        # Workspace
        self.workspace_dir = Path(".agent-workspace")
        self.workspace_dir.mkdir(exist_ok=True)

        logger.info(f"Initialized orchestrator for team {team_id}")
        logger.info(f"Repository: {self.repo_path}")
        logger.info(f"Found {len(self.tasks_config.get('features', []))} features to process")

    def _load_yaml(self, path: str) -> dict:
        """Load YAML file."""
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load {path}: {e}")
            return {}

    def execute_task(self, feature: dict) -> bool:
        """Execute a single feature task."""
        feature_name = feature.get('name', 'unknown')
        branch_name = feature.get('branch', f'feature/{feature_name}')
        description = feature.get('description', '')
        role = feature.get('role', 'Software Developer')

        logger.info(f"Starting feature: {feature_name}")
        logger.info(f"Branch: {branch_name}")

        try:
            # Create branch
            logger.info(f"Creating branch {branch_name}")
            result = self.git_ops.create_branch(branch_name)
            if not result['success']:
                logger.error(f"Failed to create branch: {result['message']}")
                return False

            # Create worktree
            worktree_path = self.workspace_dir / f"worktree-{feature_name}"
            logger.info(f"Creating worktree at {worktree_path}")
            result = self.git_ops.create_worktree(str(worktree_path), branch_name)
            if not result['success']:
                logger.error(f"Failed to create worktree: {result['message']}")
                return False

            # Execute feature development using Claude
            logger.info(f"Executing feature development with Claude")
            success = self._develop_feature(
                worktree_path=worktree_path,
                branch_name=branch_name,
                role=role,
                description=description,
                feature_name=feature_name
            )

            if success:
                logger.info(f"Feature {feature_name} completed successfully")
            else:
                logger.error(f"Feature {feature_name} failed")

            return success

        except Exception as e:
            logger.error(f"Error executing task {feature_name}: {e}")
            return False

    def _develop_feature(self, worktree_path: Path, branch_name: str,
                         role: str, description: str, feature_name: str) -> bool:
        """Develop a feature using Claude."""

        # Create system prompt
        system_prompt = f"""You are a {role} working on a software project.

Your task is to implement the following feature:

{description}

You are working in a git repository. The current branch is '{branch_name}'.
Working directory: {worktree_path}

Please implement the feature step by step:
1. Analyze what files need to be created or modified
2. Make the necessary code changes
3. Test your changes
4. Commit your work with a clear commit message

Provide a detailed summary of what you implemented."""

        # Call Claude
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": f"Please implement the feature: {feature_name}"
                    }
                ]
            )

            # Log response
            response_text = response.content[0].text
            logger.info(f"Claude response:\n{response_text}")

            # For now, we'll consider this successful if we got a response
            # In a full implementation, we would parse tool calls and execute git operations
            return True

        except Exception as e:
            logger.error(f"Error calling Claude API: {e}")
            return False

    def run(self):
        """Run the orchestrator."""
        logger.info("Starting orchestrator execution")

        features = self.tasks_config.get('features', [])
        if not features:
            logger.warning("No features found in tasks configuration")
            return

        for feature in features:
            logger.info(f"\n{'='*60}")
            self.execute_task(feature)
            logger.info(f"{'='*60}\n")

        logger.info("Orchestrator execution completed")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Simple Multi-Agent Orchestrator')
    parser.add_argument('--config', required=True, help='Path to config YAML')
    parser.add_argument('--tasks', required=True, help='Path to tasks YAML')
    parser.add_argument('--team-id', required=True, help='Team ID')

    args = parser.parse_args()

    try:
        orchestrator = SimpleOrchestrator(args.config, args.tasks, args.team_id)
        orchestrator.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
