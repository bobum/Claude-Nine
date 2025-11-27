# Monitor Agent Architecture

## Overview

Each team has a **Monitor Agent** (persona: "Monitor") that observes and reports on the activity of Dev Agents in real-time. The monitor tracks each dev agent's orchestrator subprocess and broadcasts telemetry to their respective UI cards.

## Architecture Revision

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Dashboard UI                                 │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │  Monitor Agent Card (Special Design)                            ││
│  │  ┌──────────────────────────────────────────────────────────┐  ││
│  │  │ 🔍 Monitor Status: Active                                 │  ││
│  │  │ Tracking: 3 dev agents                                    │  ││
│  │  │ Total Tokens: 15.2K ($0.082)                              │  ││
│  │  │ Active Tasks: 2                                            │  ││
│  │  │ Git Operations: 8                                          │  ││
│  │  └──────────────────────────────────────────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ Dev Agent 1  │  │ Dev Agent 2  │  │ Dev Agent 3  │              │
│  │ CPU: 12%     │  │ CPU: 8%      │  │ CPU: 5%      │              │
│  │ Mem: 256MB   │  │ Mem: 180MB   │  │ Mem: 150MB   │              │
│  │ Tokens: 5.2K │  │ Tokens: 3.1K │  │ Tokens: 2.8K │              │
│  │ Status: 🟢   │  │ Status: 🟢   │  │ Status: 🟡   │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└───────────────────────────────────────────────────────────────────┘
                              ▲
                              │ WebSocket
                              │
┌─────────────────────────────┴───────────────────────────────────────┐
│                      FastAPI Backend                                 │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │              Monitor Agent Service                              ││
│  │  - Spawns monitor subprocess per team                           ││
│  │  - Monitor tracks all dev agent subprocesses                    ││
│  │  - Broadcasts telemetry per dev agent                           ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
                              ▲
                              │
┌─────────────────────────────┴───────────────────────────────────────┐
│              Monitor Agent Subprocess (per team)                     │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │  Monitor Loop (every 2 seconds):                                ││
│  │  1. For each dev agent in team:                                 ││
│  │     - Collect process metrics (CPU, memory)                     ││
│  │     - Parse stdout/stderr for git activity                      ││
│  │     - Parse stdout/stderr for token usage                       ││
│  │     - Track activity logs                                       ││
│  │  2. Report telemetry to API via HTTP                            ││
│  │  3. Self-report monitor status                                  ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
                              ▲
                              │ observes PIDs
                              │
┌─────────────────────────────┴───────────────────────────────────────┐
│         Dev Agent Orchestrator Subprocesses (multiple)               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ Dev Agent 1  │  │ Dev Agent 2  │  │ Dev Agent 3  │              │
│  │ PID: 12345   │  │ PID: 12346   │  │ PID: 12347   │              │
│  │ Task: API    │  │ Task: UI     │  │ Task: Tests  │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Changes from Original Design

### Original (Wrong)
- TelemetryService tracked the orchestrator subprocess
- One orchestrator subprocess ran all agents (CrewAI)
- Telemetry was process-level, not agent-level

### New (Correct)
- **Monitor Agent** is a separate agent with "Monitor" persona
- Monitor subprocess tracks each dev agent's orchestrator subprocess
- Each dev agent gets its own subprocess (isolated execution)
- Monitor reports telemetry per dev agent to their respective cards
- Monitor also self-reports its own activity

## Data Flow

### 1. Team Start
```
User clicks "Start Team"
  ↓
orchestrator_service.start_team()
  ↓
For each agent in team:
  - Spawn orchestrator subprocess with work item
  - Track PID
  ↓
If team has Monitor agent:
  - Spawn monitor subprocess
  - Pass all dev agent PIDs
  - Monitor begins tracking
```

### 2. Monitor Loop (every 2 seconds)
```python
while monitoring:
    for dev_agent in team.dev_agents:
        # Collect metrics
        metrics = collect_process_metrics(dev_agent.pid)

        # Parse recent stdout/stderr
        git_activity = parse_git_activity(dev_agent.logs)
        tokens = parse_token_usage(dev_agent.logs)

        # Report to API
        await report_telemetry(
            agent_id=dev_agent.id,
            metrics=metrics,
            git_activity=git_activity,
            tokens=tokens
        )

    # Self-report monitor status
    await report_monitor_status(
        agents_tracked=len(team.dev_agents),
        total_tokens=sum(agent.tokens for agent in team.dev_agents),
        active_tasks=count_active_tasks()
    )

    await asyncio.sleep(2)
```

### 3. API Receives Telemetry
```python
@router.post("/telemetry/{agent_id}")
async def receive_telemetry(agent_id: str, data: TelemetryData):
    # Broadcast to WebSocket
    await notify_agent_telemetry(
        agent_id=agent_id,
        team_id=data.team_id,
        event="metrics_update",
        data=asdict(data)
    )
```

### 4. UI Updates
```typescript
useEffect(() => {
  ws.on('agent_telemetry', (msg) => {
    if (msg.agent_id === agent.id) {
      setTelemetry(msg.data)
    }
  })
}, [agent.id])
```

## Agent Persona: Monitor

### Database Schema Addition
```python
# Agent model already has persona_type field
# Add "monitor" to allowed persona types

PERSONA_TYPES = [
    "dev",         # Development agent
    "monitor",     # Monitoring agent (new)
    "orchestrator" # Orchestration agent
]
```

### Monitor Agent Properties
```python
{
    "name": "Agent Monitor",
    "persona_type": "monitor",
    "role": "Team Monitor",
    "goal": "Track and report dev agent activity, resource usage, and progress",
    "specialization": None,  # Not applicable
    "status": "monitoring",  # Special status
    "capabilities": [
        "process_monitoring",
        "git_activity_tracking",
        "token_usage_tracking",
        "log_aggregation",
        "real_time_reporting"
    ]
}
```

### Team Composition Rules
```python
# One team can have:
- 1 Monitor agent (optional but recommended)
- N Dev agents (1 or more)
- 1 Orchestrator agent (system-managed, not visible)

# Monitor is created automatically when team is created
# Monitor can be disabled/enabled per team
```

## Monitor Subprocess Implementation

### New File: `monitor_agent.py`
```python
"""
Monitor Agent - Tracks dev agent activity and reports telemetry

This subprocess runs alongside dev agent orchestrators and observes their
process metrics, stdout/stderr, and reports real-time telemetry to the API.
"""

import psutil
import asyncio
import httpx
import sys
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class DevAgentInfo:
    agent_id: str
    pid: int
    name: str
    work_item_id: str

class MonitorAgent:
    def __init__(
        self,
        team_id: str,
        monitor_agent_id: str,
        dev_agents: List[DevAgentInfo],
        api_url: str
    ):
        self.team_id = team_id
        self.monitor_agent_id = monitor_agent_id
        self.dev_agents = dev_agents
        self.api_url = api_url

        # Initialize collectors per dev agent
        self.collectors = {
            agent.agent_id: ProcessMetricsCollector(agent.pid)
            for agent in dev_agents
        }

    async def run(self):
        """Main monitoring loop"""
        while True:
            # Collect telemetry for each dev agent
            for dev_agent in self.dev_agents:
                try:
                    metrics = await self.collect_metrics(dev_agent)
                    await self.report_telemetry(dev_agent.agent_id, metrics)
                except Exception as e:
                    print(f"Error monitoring {dev_agent.name}: {e}")

            # Self-report monitor status
            await self.report_monitor_status()

            await asyncio.sleep(2)

    async def collect_metrics(self, dev_agent: DevAgentInfo):
        """Collect all metrics for a dev agent"""
        collector = self.collectors[dev_agent.agent_id]

        return {
            "process_metrics": await collector.collect_metrics(),
            "git_activities": [],  # Parse from logs
            "token_usage": None,   # Parse from logs
            "activity_logs": []     # Recent logs
        }

    async def report_telemetry(self, agent_id: str, metrics: dict):
        """Report telemetry to API"""
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self.api_url}/api/telemetry/{agent_id}",
                json={
                    "team_id": self.team_id,
                    "metrics": metrics
                }
            )

    async def report_monitor_status(self):
        """Report monitor's own status"""
        status = {
            "agents_tracked": len(self.dev_agents),
            "total_tokens": 0,  # Aggregate
            "active_tasks": sum(1 for a in self.dev_agents if a.pid > 0)
        }

        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self.api_url}/api/telemetry/{self.monitor_agent_id}",
                json={
                    "team_id": self.team_id,
                    "monitor_status": status
                }
            )

# Entry point
if __name__ == "__main__":
    # Parse command line args
    # team_id, monitor_agent_id, dev_agents JSON, api_url
    asyncio.run(MonitorAgent(...).run())
```

## UI Component Differentiation

### Dev Agent Card
```typescript
<Card className="dev-agent-card">
  <CardHeader>
    <Avatar>{agent.name[0]}</Avatar>
    <div>
      <h3>{agent.name}</h3>
      <Badge>{agent.status}</Badge>
    </div>
  </CardHeader>
  <CardContent>
    <MetricsGrid>
      <Metric icon={<Cpu />} label="CPU" value={`${telemetry.cpu}%`} />
      <Metric icon={<Memory />} label="RAM" value={`${telemetry.memory}MB`} />
      <Metric icon={<Coins />} label="Tokens" value={telemetry.tokens} />
      <Metric icon={<DollarSign />} label="Cost" value={`$${telemetry.cost}`} />
    </MetricsGrid>
    <ActivityFeed logs={telemetry.logs} />
  </CardContent>
</Card>
```

### Monitor Agent Card (Distinct Design)
```typescript
<Card className="monitor-agent-card special-gradient">
  <CardHeader className="monitor-header">
    <div className="monitor-icon">🔍</div>
    <div>
      <h3>Team Monitor</h3>
      <Badge variant="monitoring">Active</Badge>
    </div>
  </CardHeader>
  <CardContent>
    <div className="monitor-stats">
      <StatBlock
        icon={<Eye />}
        label="Tracking"
        value={`${monitorStatus.agents_tracked} agents`}
      />
      <StatBlock
        icon={<Activity />}
        label="Active Tasks"
        value={monitorStatus.active_tasks}
      />
      <StatBlock
        icon={<Coins />}
        label="Team Tokens"
        value={monitorStatus.total_tokens}
      />
      <StatBlock
        icon={<DollarSign />}
        label="Team Cost"
        value={`$${monitorStatus.total_cost}`}
      />
    </div>
    <GitActivityTimeline activities={monitorStatus.recent_git_activities} />
  </CardContent>
</Card>
```

## Implementation Phases

### Phase 1: Monitor Agent Infrastructure
- [ ] Create monitor_agent.py subprocess script
- [ ] Add monitor agent creation to team setup
- [ ] Implement monitor → API telemetry reporting endpoint
- [ ] Test monitor tracking single dev agent

### Phase 2: Multi-Agent Tracking
- [ ] Monitor tracks multiple dev agent PIDs
- [ ] Aggregate metrics collection
- [ ] Per-agent telemetry broadcasting
- [ ] Test with 3 dev agents

### Phase 3: UI Components
- [ ] Dev agent card component
- [ ] Monitor agent card component (distinct styling)
- [ ] Real-time WebSocket updates
- [ ] Activity timelines and charts

### Phase 4: Advanced Features
- [ ] Historical metrics storage
- [ ] Cost alerts and budgets
- [ ] Performance comparisons
- [ ] Export telemetry data

## Benefits of This Architecture

1. **Clear Separation**: Monitor agent has distinct role and responsibilities
2. **Scalable**: Monitor can track any number of dev agents
3. **Isolated**: Each dev agent runs in its own subprocess
4. **Real-time**: 2-second update cycle keeps UI responsive
5. **Extensible**: Easy to add more monitor capabilities
6. **User-Friendly**: Clear visual distinction in UI between dev agents and monitor
