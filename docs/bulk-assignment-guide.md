# Bulk Assignment Feature Guide

Complete guide to using the bulk assignment feature for work items in Claude-Nine.

## Table of Contents

1. [Overview](#overview)
2. [User Guide - Dashboard](#user-guide---dashboard)
3. [API Reference](#api-reference)
4. [Developer Integration Guide](#developer-integration-guide)
5. [Examples](#examples)
6. [Troubleshooting](#troubleshooting)

---

## Overview

The bulk assignment feature allows you to select multiple work items and assign them all to a team's work queue at once. This is essential for efficiently managing your AI development teams.

### Use Cases

- **Sprint Planning**: Assign multiple PBIs from Azure DevOps to a team
- **Issue Triage**: Bulk assign GitHub issues to the appropriate team
- **Backlog Management**: Queue up features from Jira for teams to work through
- **Quick Distribution**: Evenly distribute work across multiple teams

### How It Works

1. Work items are selected via checkboxes in the UI
2. User chooses a target team from a dropdown
3. Backend validates team and work items exist
4. All items are assigned to the team's queue
5. `assigned_at` timestamp is set for tracking
6. UI refreshes to show updated assignments

---

## User Guide - Dashboard

### Step-by-Step: Assigning Work Items

#### Step 1: Navigate to Work Items

```
Dashboard → Work Items (http://localhost:3000/work-items)
```

#### Step 2: Select Items to Assign

**Option A: Select Individual Items**
- Click the checkbox next to each work item you want to assign
- Selected items will show a blue ring around them
- Counter in header shows "Assign X Items"

**Option B: Select All Items**
- Click the master checkbox in the selection bar
- All visible items (based on current filters) are selected
- Text shows "All X items selected"

**Tip**: Use filters to narrow down items before bulk selecting:
- Filter by Status (e.g., "Queued")
- Filter by Source (e.g., "Azure DevOps")
- Filter by current Team assignment

#### Step 3: Open Bulk Assign Modal

Click the green **"Assign X Items"** button that appears in the header.

#### Step 4: Choose Target Team

In the modal:
1. Select a team from the dropdown
   - Teams are listed as: "Team Name - Product"
2. Click **"Assign to Queue"** button
3. Wait for confirmation (items will refresh)

#### Step 5: Verify Assignment

- Selection clears automatically
- Work items refresh to show new team assignments
- Check the "Team" label on each item to confirm

### UI Features

#### Selection Indicators

- **Blue Ring**: Around selected work item cards
- **Counter**: "X items selected" in header and selection bar
- **Clear Button**: Quickly deselect all items

#### Bulk Assign Modal

```
┌─────────────────────────────────────────┐
│ Assign 5 Work Items to Team            │
│                                         │
│ Select a team to assign the selected   │
│ work items to their queue               │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ Select a team...                  ▼ │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ ┌──────────────┐  ┌──────────────────┐ │
│ │Assign to Queue│  │     Cancel       │ │
│ └──────────────┘  └──────────────────┘ │
└─────────────────────────────────────────┘
```

### Keyboard Shortcuts

- **Checkbox**: Click or Space to toggle
- **Modal**: Esc to close (cancel)

---

## API Reference

### POST /api/work-items/bulk-assign

Assign multiple work items to a team's queue in a single operation.

#### Request

**Endpoint**: `POST /api/work-items/bulk-assign`

**Headers**:
```http
Content-Type: application/json
```

**Body**:
```json
{
  "work_item_ids": [
    "uuid-of-item-1",
    "uuid-of-item-2",
    "uuid-of-item-3"
  ],
  "team_id": "uuid-of-target-team"
}
```

**Schema**:
```typescript
interface BulkAssignRequest {
  work_item_ids: string[];  // Array of work item UUIDs
  team_id: string;          // Target team UUID
}
```

#### Response

**Success (200 OK)**:
```json
[
  {
    "id": "uuid-of-item-1",
    "external_id": "PBI-123",
    "source": "azure_devops",
    "title": "Implement user authentication",
    "description": "Add OAuth2 authentication",
    "status": "queued",
    "priority": 1,
    "story_points": 8,
    "team_id": "uuid-of-target-team",
    "assigned_at": "2025-11-25T10:30:00Z",
    "created_at": "2025-11-20T08:00:00Z",
    "updated_at": "2025-11-25T10:30:00Z"
  },
  // ... more work items
]
```

**Error Responses**:

```json
// 404 - Team Not Found
{
  "detail": "Team not found"
}

// 404 - Work Item(s) Not Found
{
  "detail": "One or more work items not found"
}

// 422 - Validation Error
{
  "detail": [
    {
      "loc": ["body", "team_id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

#### Behavior

1. **Validates Team**: Checks that `team_id` exists in database
2. **Validates Work Items**: Ensures all IDs in `work_item_ids` exist
3. **Atomic Operation**: Either all items are assigned or none (transaction)
4. **Sets Timestamp**: Updates `assigned_at` for newly assigned items
5. **Preserves Status**: Does not change work item status
6. **Returns Updated Items**: All modified work items with new data

#### Performance

- Optimized for bulk operations (single query for validation)
- Transaction ensures consistency
- Typical response time: <100ms for up to 50 items

---

## Developer Integration Guide

### Frontend Integration

#### Using the API Client

The TypeScript API client provides a simple function:

```typescript
import { bulkAssignWorkItems } from "@/lib/api";

// Assign multiple items to a team
const selectedIds = ["uuid-1", "uuid-2", "uuid-3"];
const targetTeamId = "team-uuid";

try {
  const updatedItems = await bulkAssignWorkItems(selectedIds, targetTeamId);
  console.log(`Assigned ${updatedItems.length} items to team`);
  // Refresh your UI with updatedItems
} catch (error) {
  console.error("Bulk assignment failed:", error);
  // Show error to user
}
```

#### React Component Example

```typescript
import { useState } from "react";
import { bulkAssignWorkItems, type WorkItem } from "@/lib/api";

function WorkItemsList() {
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [workItems, setWorkItems] = useState<WorkItem[]>([]);

  const handleBulkAssign = async (teamId: string) => {
    try {
      const itemIds = Array.from(selectedItems);
      const updated = await bulkAssignWorkItems(itemIds, teamId);

      // Update local state
      setWorkItems(prev =>
        prev.map(item =>
          updated.find(u => u.id === item.id) || item
        )
      );

      // Clear selection
      setSelectedItems(new Set());

      // Show success message
      alert(`${updated.length} items assigned successfully!`);
    } catch (error) {
      alert("Failed to assign items");
    }
  };

  // ... rest of component
}
```

### Backend Integration

#### Database Models

The bulk assignment uses these SQLAlchemy models:

```python
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid

class WorkItem(Base):
    __tablename__ = "work_items"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    team_id = Column(GUID(), ForeignKey("teams.id"), nullable=True)
    external_id = Column(String, nullable=False)
    source = Column(String, nullable=False)
    title = Column(String, nullable=False)
    status = Column(String, default="queued")
    priority = Column(Integer, default=0)
    assigned_at = Column(DateTime, nullable=True)
    # ... more fields
```

#### Custom Endpoint Implementation

If you need to customize the bulk assignment logic:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

@router.post("/bulk-assign-custom")
def custom_bulk_assign(
    request: BulkAssignRequest,
    db: Session = Depends(get_db)
):
    # Verify team
    team = db.query(Team).filter(Team.id == request.team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Get work items
    work_items = db.query(WorkItem).filter(
        WorkItem.id.in_(request.work_item_ids)
    ).all()

    # Custom logic: Check team capacity
    if len(team.work_items) + len(work_items) > team.max_capacity:
        raise HTTPException(
            status_code=400,
            detail="Team at capacity"
        )

    # Assign items
    for work_item in work_items:
        work_item.team_id = request.team_id
        work_item.assigned_at = datetime.utcnow()
        # Custom: Auto-prioritize based on story points
        work_item.priority = work_item.story_points or 0

    db.commit()

    # Refresh and return
    for item in work_items:
        db.refresh(item)

    return work_items
```

---

## Examples

### Example 1: Sprint Planning Workflow

Assign all "High Priority" items to the Frontend team:

```bash
# Step 1: Get high priority items
curl -s "http://localhost:8000/api/work-items/?priority=1&status=queued" \
  | jq -r '.[].id'

# Output:
# uuid-item-1
# uuid-item-2
# uuid-item-3

# Step 2: Get Frontend team ID
curl -s "http://localhost:8000/api/teams/" \
  | jq -r '.[] | select(.name=="Frontend Team") | .id'

# Output:
# uuid-team-frontend

# Step 3: Bulk assign
curl -X POST "http://localhost:8000/api/work-items/bulk-assign" \
  -H "Content-Type: application/json" \
  -d '{
    "work_item_ids": [
      "uuid-item-1",
      "uuid-item-2",
      "uuid-item-3"
    ],
    "team_id": "uuid-team-frontend"
  }'
```

### Example 2: TypeScript Automation

Automatically distribute unassigned items across teams:

```typescript
import { getWorkItems, getTeams, bulkAssignWorkItems } from "@/lib/api";

async function distributeWorkItems() {
  // Get unassigned items
  const unassigned = await getWorkItems({ status: "queued" });
  const unassignedItems = unassigned.filter(item => !item.team_id);

  // Get all active teams
  const teams = await getTeams();
  const activeTeams = teams.filter(t => t.status === "active");

  if (activeTeams.length === 0) {
    throw new Error("No active teams available");
  }

  // Distribute evenly
  const itemsPerTeam = Math.ceil(unassignedItems.length / activeTeams.length);

  for (let i = 0; i < activeTeams.length; i++) {
    const start = i * itemsPerTeam;
    const end = start + itemsPerTeam;
    const itemsForTeam = unassignedItems.slice(start, end);

    if (itemsForTeam.length > 0) {
      const itemIds = itemsForTeam.map(item => item.id);
      await bulkAssignWorkItems(itemIds, activeTeams[i].id);
      console.log(
        `Assigned ${itemIds.length} items to ${activeTeams[i].name}`
      );
    }
  }
}

// Run distribution
distributeWorkItems()
  .then(() => console.log("Distribution complete!"))
  .catch(console.error);
```

### Example 3: Python Script for Azure DevOps Integration

Sync PBIs from Azure DevOps and bulk assign:

```python
import requests
from typing import List

API_BASE = "http://localhost:8000"

def sync_and_assign_pbi_items(sprint_id: str, team_id: str):
    # Fetch from Azure DevOps (simplified)
    azure_pbis = fetch_azure_devops_pbis(sprint_id)

    # Create work items in Claude-Nine
    created_ids: List[str] = []
    for pbi in azure_pbis:
        response = requests.post(
            f"{API_BASE}/api/work-items/",
            json={
                "external_id": pbi["id"],
                "source": "azure_devops",
                "title": pbi["title"],
                "description": pbi["description"],
                "priority": pbi["priority"],
                "story_points": pbi["story_points"],
                "external_url": pbi["url"]
            }
        )
        if response.ok:
            created_ids.append(response.json()["id"])

    # Bulk assign all to team
    if created_ids:
        response = requests.post(
            f"{API_BASE}/api/work-items/bulk-assign",
            json={
                "work_item_ids": created_ids,
                "team_id": team_id
            }
        )
        print(f"Assigned {len(created_ids)} PBIs to team")
        return response.json()

    return []

# Usage
sync_and_assign_pbi_items(
    sprint_id="Sprint-42",
    team_id="uuid-backend-team"
)
```

---

## Troubleshooting

### Issue: "Team not found" Error

**Cause**: Invalid team UUID or team was deleted

**Solution**:
```bash
# Verify team exists
curl http://localhost:8000/api/teams/ | jq

# Check specific team
curl http://localhost:8000/api/teams/{team_id}
```

### Issue: "One or more work items not found"

**Cause**: One or more work item IDs don't exist or were deleted

**Solution**:
```typescript
// Validate IDs before bulk assign
const validIds = await Promise.all(
  itemIds.map(async (id) => {
    try {
      await fetch(`${API_BASE}/api/work-items/${id}`);
      return id;
    } catch {
      return null;
    }
  })
).then(ids => ids.filter(Boolean));

// Only assign valid items
await bulkAssignWorkItems(validIds, teamId);
```

### Issue: Items Not Showing as Assigned in UI

**Cause**: UI state not refreshed after assignment

**Solution**:
```typescript
// Always reload data after bulk assign
await bulkAssignWorkItems(itemIds, teamId);
await loadData(); // Refresh work items list
```

### Issue: Slow Performance with Many Items

**Cause**: Assigning hundreds of items at once

**Solution**:
```typescript
// Batch large assignments
const BATCH_SIZE = 50;

async function batchAssign(itemIds: string[], teamId: string) {
  for (let i = 0; i < itemIds.length; i += BATCH_SIZE) {
    const batch = itemIds.slice(i, i + BATCH_SIZE);
    await bulkAssignWorkItems(batch, teamId);
    console.log(`Assigned batch ${i / BATCH_SIZE + 1}`);
  }
}
```

### Issue: Transaction Timeout

**Cause**: Database connection pool exhausted

**Solution**:
```python
# In database.py, increase pool size
engine = create_engine(
    DATABASE_URL,
    pool_size=20,  # Increase from default 5
    max_overflow=40  # Increase from default 10
)
```

---

## Best Practices

### 1. Use Filters Before Bulk Selection

Filter work items first to avoid accidentally assigning wrong items:
- Filter by status (e.g., only "queued" items)
- Filter by source (e.g., only "azure_devops")
- Filter by current team (e.g., only "Unassigned")

### 2. Verify Selection Count

Always check the selection count before assigning:
- Header shows "Assign X Items"
- Selection bar shows "X items selected"
- Modal confirms "Assign X Work Items to Team"

### 3. Start Small

When first using bulk assignment:
1. Start with 2-3 items
2. Verify assignment worked correctly
3. Scale up to larger batches

### 4. Use Descriptive Team Names

Help users pick the right team:
- Good: "Frontend Team - E-commerce"
- Bad: "Team 1"

### 5. Monitor Assignment History

Track assignments through the `assigned_at` timestamp:
```sql
SELECT
  title,
  team_id,
  assigned_at,
  status
FROM work_items
WHERE assigned_at > NOW() - INTERVAL '1 day'
ORDER BY assigned_at DESC;
```

---

## Related Documentation

- [Quick Start Guide](./quick-start.md) - Get Claude-Nine running
- [Database Schema](./database-schema.md) - Full schema reference
- [API Documentation](http://localhost:8000/docs) - Interactive API docs
- [Vision & Roadmap](../VISION.md) - Claude-Nine overview

---

**Questions or Issues?**

- Check the [Troubleshooting](#troubleshooting) section
- Review [Examples](#examples) for common patterns
- Open an issue on GitHub
