"""Reset database and seed with test data"""
import os
import sys
import time
import requests

API_URL = "http://localhost:8000/api"

def wait_for_api():
    """Wait for API to be ready"""
    print("Waiting for API to be ready...")
    for i in range(30):
        try:
            resp = requests.get(f"{API_URL}/teams/", timeout=2)
            if resp.status_code in [200, 307]:
                print("API is ready!")
                return True
        except:
            pass
        time.sleep(1)
    print("API not responding after 30 seconds")
    return False

def create_team():
    """Create the test team"""
    team_data = {
        "name": "Schematics Team",
        "product": "Schematics",
        "repo_path": "C:/projects/schematics",
        "main_branch": "main",
        "max_concurrent_tasks": 4,
        "status": "active"
    }

    resp = requests.post(f"{API_URL}/teams/", json=team_data)
    if resp.status_code in [200, 201]:
        team = resp.json()
        print(f"Created team: {team['name']} (ID: {team['id']})")
        return team
    else:
        print(f"Failed to create team: {resp.status_code} - {resp.text}")
        return None

def create_work_items(team_id):
    """Create test work items"""
    work_items = [
        {
            "external_id": "TEST-001",
            "source": "manual",
            "title": "Add input validation to user registration form",
            "description": "Add client-side and server-side validation for the user registration form fields.",
            "acceptance_criteria": "- Email format validation\n- Password strength requirements\n- All fields required",
            "status": "queued",
            "priority": 1
        },
        {
            "external_id": "TEST-002",
            "source": "manual",
            "title": "Create API endpoint for user preferences",
            "description": "Create a new REST API endpoint to get and update user preferences.",
            "acceptance_criteria": "- GET /api/preferences returns user prefs\n- PUT /api/preferences updates prefs\n- Proper error handling",
            "status": "queued",
            "priority": 2
        },
        {
            "external_id": "TEST-003",
            "source": "manual",
            "title": "Add unit tests for authentication module",
            "description": "Write comprehensive unit tests for the authentication module.",
            "acceptance_criteria": "- Test login flow\n- Test logout flow\n- Test token refresh\n- 80% code coverage",
            "status": "queued",
            "priority": 3
        },
        {
            "external_id": "TEST-004",
            "source": "manual",
            "title": "Implement dark mode toggle",
            "description": "Add a toggle in settings to switch between light and dark mode.",
            "acceptance_criteria": "- Toggle persists across sessions\n- Smooth transition animation\n- All components support both modes",
            "status": "queued",
            "priority": 4
        }
    ]

    created = []
    for item in work_items:
        item["team_id"] = team_id
        resp = requests.post(f"{API_URL}/work-items/", json=item)
        if resp.status_code in [200, 201]:
            wi = resp.json()
            print(f"Created work item: {wi['external_id']} - {wi['title']}")
            created.append(wi)
        else:
            print(f"Failed to create work item {item['external_id']}: {resp.status_code} - {resp.text}")

    return created

def main():
    print("=" * 60)
    print("Claude-Nine Demo - Database Reset & Seed")
    print("=" * 60)

    # Delete database
    db_path = os.path.join(os.path.dirname(__file__), "claude_nine.db")
    if os.path.exists(db_path):
        print(f"\nDeleting database: {db_path}")
        os.remove(db_path)
        print("Database deleted.")
    else:
        print(f"\nNo database found at {db_path}")

    print("\nPlease restart the API server to recreate tables.")
    print("Then run this script again with --seed flag to add test data.")
    print("\nOr if API is already running, press Enter to seed now...")

    if "--seed" in sys.argv or input().strip() == "":
        if not wait_for_api():
            sys.exit(1)

        print("\n--- Creating Team ---")
        team = create_team()
        if not team:
            sys.exit(1)

        print("\n--- Creating Work Items ---")
        work_items = create_work_items(team["id"])

        print("\n" + "=" * 60)
        print("SETUP COMPLETE!")
        print("=" * 60)
        print(f"\nTeam ID: {team['id']}")
        print(f"Work Items: {len(work_items)} queued")
        print(f"\nOpen dashboard: http://localhost:3001/teams/{team['id']}")
        print("\nClick START to run the orchestrator!")

if __name__ == "__main__":
    main()
