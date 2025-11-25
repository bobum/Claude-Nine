#!/bin/bash
# Test script for Claude-Nine API

BASE_URL="http://localhost:8000"

echo "🧪 Testing Claude-Nine API..."
echo ""

# Health checks
echo "1️⃣ Health Check"
curl -s $BASE_URL/health | jq
echo ""

echo "2️⃣ Database Health Check"
curl -s $BASE_URL/health/db | jq
echo ""

# Create a team
echo "3️⃣ Creating a team..."
TEAM_RESPONSE=$(curl -s -X POST $BASE_URL/api/teams/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "E-Commerce Team",
    "product": "ShopifyClone",
    "repo_path": "/repos/shopify-clone"
  }')
echo $TEAM_RESPONSE | jq
TEAM_ID=$(echo $TEAM_RESPONSE | jq -r '.id')
echo "Team ID: $TEAM_ID"
echo ""

# List teams
echo "4️⃣ Listing all teams..."
curl -s $BASE_URL/api/teams/ | jq
echo ""

# Add agents to team
echo "5️⃣ Adding backend agent..."
curl -s -X POST $BASE_URL/api/teams/$TEAM_ID/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "backend_agent",
    "role": "Backend Developer",
    "goal": "Build robust APIs and backend services"
  }' | jq
echo ""

echo "6️⃣ Adding frontend agent..."
curl -s -X POST $BASE_URL/api/teams/$TEAM_ID/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "frontend_agent",
    "role": "Frontend Developer",
    "goal": "Create responsive user interfaces"
  }' | jq
echo ""

# Get team with agents
echo "7️⃣ Getting team with agents..."
curl -s $BASE_URL/api/teams/$TEAM_ID | jq
echo ""

# Create work item
echo "8️⃣ Creating work item..."
WORK_ITEM_RESPONSE=$(curl -s -X POST $BASE_URL/api/work-items/ \
  -H "Content-Type: application/json" \
  -d '{
    "external_id": "PBI-4521",
    "source": "azure_devops",
    "title": "Implement user authentication with OAuth",
    "description": "Add OAuth 2.0 authentication flow",
    "priority": 1,
    "story_points": 8,
    "team_id": "'$TEAM_ID'"
  }')
echo $WORK_ITEM_RESPONSE | jq
echo ""

# List work items
echo "9️⃣ Listing work items..."
curl -s $BASE_URL/api/work-items/ | jq
echo ""

# Start the team
echo "🔟 Starting the team..."
curl -s -X POST $BASE_URL/api/teams/$TEAM_ID/start | jq
echo ""

# Get team status
echo "1️⃣1️⃣ Getting updated team status..."
curl -s $BASE_URL/api/teams/$TEAM_ID | jq
echo ""

echo "✅ All tests complete!"
