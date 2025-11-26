"""
Local Work Item Manager for CLAUDE-9

A standalone work item tracking system that stores items in SQLite,
supports team assignment, and exports to CLAUDE-9 task format.
"""

import sqlite3
import yaml
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WorkItemManager:
    """
    Manages work items in a local SQLite database.

    Features:
    - Create work items without external dependencies
    - Assign work items to teams
    - Export to CLAUDE-9 YAML format
    - Track status and priority
    - Add comments and attachments
    """

    def __init__(self, db_path: str = ".agent-workspace/work_items.db"):
        """
        Initialize the work item manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        self._create_tables()

        logger.info(f"Initialized WorkItemManager with database at {db_path}")

    def _create_tables(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()

        # Teams table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Work items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS work_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                work_item_type TEXT DEFAULT 'feature',
                status TEXT DEFAULT 'new',
                priority TEXT DEFAULT 'medium',
                team_id INTEGER,
                assigned_to TEXT,
                branch_name TEXT,
                estimated_hours REAL,
                tags TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams(id)
            )
        ''')

        # Comments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_item_id INTEGER NOT NULL,
                author TEXT,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (work_item_id) REFERENCES work_items(id) ON DELETE CASCADE
            )
        ''')

        # Attachments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_item_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (work_item_id) REFERENCES work_items(id) ON DELETE CASCADE
            )
        ''')

        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_work_items_status ON work_items(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_work_items_team ON work_items(team_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_work_items_priority ON work_items(priority)')

        self.conn.commit()
        logger.info("Database tables created/verified")

    # ==================== TEAM MANAGEMENT ====================

    def create_team(self, name: str, description: str = "") -> int:
        """
        Create a new team.

        Args:
            name: Team name
            description: Team description

        Returns:
            int: Team ID
        """
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO teams (name, description) VALUES (?, ?)',
            (name, description)
        )
        self.conn.commit()
        team_id = cursor.lastrowid

        logger.info(f"Created team: {name} (ID: {team_id})")
        return team_id

    def list_teams(self) -> List[Dict]:
        """List all teams."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM teams ORDER BY name')
        teams = [dict(row) for row in cursor.fetchall()]
        return teams

    def get_team(self, team_id: int) -> Optional[Dict]:
        """Get team by ID."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM teams WHERE id = ?', (team_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    # ==================== WORK ITEM MANAGEMENT ====================

    def create_work_item(
        self,
        title: str,
        description: str = "",
        work_item_type: str = "feature",
        priority: str = "medium",
        team_id: Optional[int] = None,
        assigned_to: Optional[str] = None,
        tags: Optional[List[str]] = None,
        estimated_hours: Optional[float] = None,
        metadata: Optional[Dict] = None
    ) -> int:
        """
        Create a new work item.

        Args:
            title: Work item title
            description: Detailed description
            work_item_type: Type (feature, bug, task, story, epic)
            priority: Priority (low, medium, high, critical)
            team_id: Assigned team ID
            assigned_to: Person assigned to
            tags: List of tags
            estimated_hours: Estimated effort in hours
            metadata: Additional metadata as dict

        Returns:
            int: Work item ID
        """
        # Generate branch name
        branch_name = f"{work_item_type}/{title.lower().replace(' ', '-')}"

        # Serialize tags and metadata
        tags_json = json.dumps(tags) if tags else None
        metadata_json = json.dumps(metadata) if metadata else None

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO work_items (
                title, description, work_item_type, priority, team_id,
                assigned_to, branch_name, estimated_hours, tags, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            title, description, work_item_type, priority, team_id,
            assigned_to, branch_name, estimated_hours, tags_json, metadata_json
        ))
        self.conn.commit()
        work_item_id = cursor.lastrowid

        logger.info(f"Created work item: {title} (ID: {work_item_id})")
        return work_item_id

    def update_work_item(
        self,
        work_item_id: int,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        team_id: Optional[int] = None,
        assigned_to: Optional[str] = None
    ) -> bool:
        """Update work item fields."""
        updates = []
        params = []

        if status:
            updates.append('status = ?')
            params.append(status)
        if priority:
            updates.append('priority = ?')
            params.append(priority)
        if team_id is not None:
            updates.append('team_id = ?')
            params.append(team_id)
        if assigned_to is not None:
            updates.append('assigned_to = ?')
            params.append(assigned_to)

        if not updates:
            return False

        updates.append('updated_at = CURRENT_TIMESTAMP')
        params.append(work_item_id)

        cursor = self.conn.cursor()
        query = f"UPDATE work_items SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        self.conn.commit()

        logger.info(f"Updated work item {work_item_id}")
        return True

    def get_work_item(self, work_item_id: int) -> Optional[Dict]:
        """Get work item by ID."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT wi.*, t.name as team_name
            FROM work_items wi
            LEFT JOIN teams t ON wi.team_id = t.id
            WHERE wi.id = ?
        ''', (work_item_id,))
        row = cursor.fetchone()

        if not row:
            return None

        item = dict(row)

        # Deserialize JSON fields
        if item['tags']:
            item['tags'] = json.loads(item['tags'])
        if item['metadata']:
            item['metadata'] = json.loads(item['metadata'])

        return item

    def list_work_items(
        self,
        status: Optional[str] = None,
        team_id: Optional[int] = None,
        work_item_type: Optional[str] = None,
        assigned_to: Optional[str] = None
    ) -> List[Dict]:
        """
        List work items with optional filters.

        Args:
            status: Filter by status
            team_id: Filter by team
            work_item_type: Filter by type
            assigned_to: Filter by assignee

        Returns:
            List of work items
        """
        query = '''
            SELECT wi.*, t.name as team_name
            FROM work_items wi
            LEFT JOIN teams t ON wi.team_id = t.id
            WHERE 1=1
        '''
        params = []

        if status:
            query += ' AND wi.status = ?'
            params.append(status)
        if team_id:
            query += ' AND wi.team_id = ?'
            params.append(team_id)
        if work_item_type:
            query += ' AND wi.work_item_type = ?'
            params.append(work_item_type)
        if assigned_to:
            query += ' AND wi.assigned_to = ?'
            params.append(assigned_to)

        query += ' ORDER BY wi.priority DESC, wi.created_at DESC'

        cursor = self.conn.cursor()
        cursor.execute(query, params)

        items = []
        for row in cursor.fetchall():
            item = dict(row)
            if item['tags']:
                item['tags'] = json.loads(item['tags'])
            if item['metadata']:
                item['metadata'] = json.loads(item['metadata'])
            items.append(item)

        return items

    # ==================== COMMENTS ====================

    def add_comment(self, work_item_id: int, author: str, content: str) -> int:
        """Add a comment to a work item."""
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO comments (work_item_id, author, content) VALUES (?, ?, ?)',
            (work_item_id, author, content)
        )
        self.conn.commit()

        logger.info(f"Added comment to work item {work_item_id}")
        return cursor.lastrowid

    def get_comments(self, work_item_id: int) -> List[Dict]:
        """Get all comments for a work item."""
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT * FROM comments WHERE work_item_id = ? ORDER BY created_at',
            (work_item_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    # ==================== CLAUDE-9 INTEGRATION ====================

    def export_to_claude9_yaml(
        self,
        output_file: str,
        status: str = "ready",
        team_id: Optional[int] = None
    ) -> str:
        """
        Export work items to CLAUDE-9 YAML format.

        Args:
            output_file: Output YAML file path
            status: Export items with this status (default: "ready")
            team_id: Optional team filter

        Returns:
            str: Path to generated YAML file
        """
        # Get work items
        work_items = self.list_work_items(status=status, team_id=team_id)

        if not work_items:
            logger.warning(f"No work items found with status '{status}'")
            return output_file

        # Convert to CLAUDE-9 task format
        features = []
        for item in work_items:
            # Build description with details
            description_parts = [item['description']]

            if item['assigned_to']:
                description_parts.append(f"\nAssigned to: {item['assigned_to']}")

            if item['estimated_hours']:
                description_parts.append(f"Estimated: {item['estimated_hours']} hours")

            if item['tags']:
                description_parts.append(f"Tags: {', '.join(item['tags'])}")

            # Get comments
            comments = self.get_comments(item['id'])
            if comments:
                description_parts.append("\n\nComments:")
                for comment in comments:
                    description_parts.append(f"- {comment['author']}: {comment['content']}")

            feature = {
                'name': item['title'].lower().replace(' ', '_'),
                'role': f"{item['work_item_type'].title()} Developer",
                'goal': f"Implement {item['title']}",
                'branch': item['branch_name'],
                'description': '\n'.join(description_parts),
                'expected_output': f"Complete {item['work_item_type']}: {item['title']}"
            }

            features.append(feature)

        # Write YAML
        output_data = {'features': features}

        with open(output_file, 'w') as f:
            yaml.dump(output_data, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Exported {len(features)} work items to {output_file}")
        return output_file

    def mark_as_complete(self, work_item_id: int) -> bool:
        """Mark work item as complete."""
        return self.update_work_item(work_item_id, status='completed')

    def mark_as_in_progress(self, work_item_id: int) -> bool:
        """Mark work item as in progress."""
        return self.update_work_item(work_item_id, status='in_progress')

    def mark_as_ready(self, work_item_id: int) -> bool:
        """Mark work item as ready for CLAUDE-9."""
        return self.update_work_item(work_item_id, status='ready')

    # ==================== REPORTING ====================

    def get_team_summary(self, team_id: int) -> Dict:
        """Get summary statistics for a team."""
        cursor = self.conn.cursor()

        # Count by status
        cursor.execute('''
            SELECT status, COUNT(*) as count
            FROM work_items
            WHERE team_id = ?
            GROUP BY status
        ''', (team_id,))

        status_counts = {row['status']: row['count'] for row in cursor.fetchall()}

        # Count by type
        cursor.execute('''
            SELECT work_item_type, COUNT(*) as count
            FROM work_items
            WHERE team_id = ?
            GROUP BY work_item_type
        ''', (team_id,))

        type_counts = {row['work_item_type']: row['count'] for row in cursor.fetchall()}

        # Total estimated hours
        cursor.execute('''
            SELECT SUM(estimated_hours) as total_hours
            FROM work_items
            WHERE team_id = ?
        ''', (team_id,))

        total_hours = cursor.fetchone()['total_hours'] or 0

        team = self.get_team(team_id)

        return {
            'team': team,
            'status_counts': status_counts,
            'type_counts': type_counts,
            'total_estimated_hours': total_hours
        }

    def close(self):
        """Close database connection."""
        self.conn.close()
        logger.info("Database connection closed")


# ==================== EXAMPLE USAGE ====================

if __name__ == "__main__":
    # Example: Create work items and export to CLAUDE-9

    manager = WorkItemManager()

    # Create teams
    backend_team = manager.create_team("Backend Team", "Backend development team")
    frontend_team = manager.create_team("Frontend Team", "Frontend development team")

    # Create work items
    auth_id = manager.create_work_item(
        title="User Authentication System",
        description="Implement JWT-based authentication with login, register, and token refresh",
        work_item_type="feature",
        priority="high",
        team_id=backend_team,
        assigned_to="Alice",
        tags=["auth", "security", "backend"],
        estimated_hours=16.0
    )

    logging_id = manager.create_work_item(
        title="API Request Logging",
        description="Add Winston logging for all API requests with request/response tracking",
        work_item_type="feature",
        priority="medium",
        team_id=backend_team,
        assigned_to="Bob",
        tags=["logging", "observability"],
        estimated_hours=8.0
    )

    ui_id = manager.create_work_item(
        title="Dashboard UI Components",
        description="Create reusable React components for dashboard",
        work_item_type="feature",
        priority="high",
        team_id=frontend_team,
        assigned_to="Carol",
        tags=["ui", "react", "components"],
        estimated_hours=24.0
    )

    # Add comments
    manager.add_comment(auth_id, "Alice", "Need to decide on token expiration policy")
    manager.add_comment(auth_id, "Manager", "Let's use 24h expiration with 7d refresh tokens")

    # Mark items as ready for CLAUDE-9
    manager.mark_as_ready(auth_id)
    manager.mark_as_ready(logging_id)

    # Export to CLAUDE-9 format
    manager.export_to_claude9_yaml(
        'tasks/work-items.yaml',
        status='ready',
        team_id=backend_team
    )

    # Get team summary
    summary = manager.get_team_summary(backend_team)
    print(f"\nTeam Summary for {summary['team']['name']}:")
    print(f"  Status counts: {summary['status_counts']}")
    print(f"  Type counts: {summary['type_counts']}")
    print(f"  Total estimated hours: {summary['total_estimated_hours']}")

    manager.close()
