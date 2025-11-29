#!/usr/bin/env python3
"""
Seed script for Claude-Nine test data.
Creates a team for the schematics project and 4 test work items.

Run this after starting the API at least once (to create the database):
    cd api
    python seed_test_data.py
"""

import sqlite3
import uuid
from datetime import datetime

DB_PATH = "claude_nine.db"

def get_connection():
    """Get database connection."""
    return sqlite3.connect(DB_PATH)

def seed_data():
    """Seed the database with test team and work items."""
    conn = get_connection()
    cursor = conn.cursor()

    # Check if team already exists
    cursor.execute("SELECT id FROM teams WHERE name = 'Schematics Test Team'")
    existing_team = cursor.fetchone()

    if existing_team:
        team_id = existing_team[0]
        print(f"Team already exists with ID: {team_id}")

        # Clear existing work items for this team to start fresh
        cursor.execute("DELETE FROM work_items WHERE team_id = ?", (team_id,))
        print("Cleared existing work items for team")
    else:
        # Create the team
        team_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        cursor.execute("""
            INSERT INTO teams (id, name, product, repo_path, main_branch, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            team_id,
            "Schematics Test Team",
            "Visual Connection Schematics App",
            "C:/projects/schematics",
            "main",
            "stopped",
            now,
            now
        ))
        print(f"Created team with ID: {team_id}")

    # Create 4 test work items
    work_items = [
        {
            "external_id": "TEST-001",
            "source": "manual",
            "title": "Add Export to PNG Feature",
            "description": """Implement the ability to export the current schematic view as a PNG image.

Requirements:
- Add an "Export" button to the toolbar
- When clicked, capture the current canvas/view
- Save as PNG with reasonable quality
- Show a success toast notification after export
- Use browser's download functionality

Technical notes:
- Use html2canvas or similar library
- Handle any cross-origin issues with images
- Ensure dark mode colors are captured correctly""",
            "acceptance_criteria": """- Export button visible in toolbar
- Clicking export downloads a PNG file
- PNG includes all visible schematic elements
- Works in both light and dark modes
- Success notification shown after export""",
            "priority": 1,
            "story_points": 3
        },
        {
            "external_id": "TEST-002",
            "source": "manual",
            "title": "Add Zoom Controls",
            "description": """Add zoom in/out controls to the schematic viewer.

Requirements:
- Add zoom in (+) and zoom out (-) buttons
- Add a zoom level indicator (e.g., "100%")
- Support keyboard shortcuts (Ctrl/Cmd + Plus/Minus)
- Add "Fit to Screen" button to auto-fit the schematic
- Smooth zoom transitions

Technical notes:
- Use CSS transform scale or SVG viewBox
- Maintain center point during zoom
- Set reasonable min/max zoom levels (25% - 400%)""",
            "acceptance_criteria": """- Zoom in/out buttons visible and functional
- Zoom level indicator shows current zoom percentage
- Keyboard shortcuts work for zooming
- Fit to Screen button auto-scales to fit viewport
- Zoom transitions are smooth""",
            "priority": 2,
            "story_points": 5
        },
        {
            "external_id": "TEST-003",
            "source": "manual",
            "title": "Add Connection Search/Filter",
            "description": """Implement a search feature to find and highlight specific connections or components.

Requirements:
- Add a search input field in the header
- Search by component name or connection label
- Highlight matching items in the schematic
- Show count of matches
- Clear search button to reset

Technical notes:
- Use case-insensitive search
- Debounce search input (300ms)
- Highlight with contrasting color/glow effect
- Scroll to first match if off-screen""",
            "acceptance_criteria": """- Search input visible in header area
- Typing filters/highlights matching elements
- Match count displayed next to search
- Clear button resets highlights
- Works in both light and dark modes""",
            "priority": 3,
            "story_points": 3
        },
        {
            "external_id": "TEST-004",
            "source": "manual",
            "title": "Add Print Stylesheet",
            "description": """Create a print-optimized stylesheet for printing schematics.

Requirements:
- Add print-specific CSS styles
- Hide UI elements (toolbar, theme toggle) when printing
- Optimize colors for print (avoid dark backgrounds)
- Ensure schematic fits on page
- Add page header with title/date

Technical notes:
- Use @media print CSS rules
- Force light colors for print
- Consider page orientation (landscape for wide schematics)
- Test with browser print preview""",
            "acceptance_criteria": """- Ctrl+P shows print-optimized view
- No UI chrome visible in print
- Colors optimized for paper printing
- Schematic scales to fit page
- Header shows document title and date""",
            "priority": 4,
            "story_points": 2
        }
    ]

    now = datetime.utcnow().isoformat()

    for item in work_items:
        work_item_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO work_items (
                id, team_id, external_id, source, title, description,
                acceptance_criteria, status, priority, story_points,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            work_item_id,
            team_id,
            item["external_id"],
            item["source"],
            item["title"],
            item["description"],
            item["acceptance_criteria"],
            "queued",
            item["priority"],
            item["story_points"],
            now,
            now
        ))
        print(f"Created work item: {item['external_id']} - {item['title']}")

    conn.commit()
    conn.close()

    print(f"\nDone! Created team and 4 work items.")
    print(f"Team ID: {team_id}")
    print(f"\nTo reset schematics repo after testing:")
    print(f"  cd C:/projects/schematics")
    print(f"  git checkout main")
    print(f"  git reset --hard origin/main")
    print(f"  git clean -fd")
    print(f"  git branch | grep -v main | xargs git branch -D")

if __name__ == "__main__":
    import os

    # Change to api directory if needed
    if not os.path.exists(DB_PATH):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)

    if not os.path.exists(DB_PATH):
        print(f"Error: Database '{DB_PATH}' not found.")
        print("Please start the API first to create the database:")
        print("  cd api && python -m uvicorn app.main:app --reload")
        exit(1)

    seed_data()
