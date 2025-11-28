# Agent Telemetry Architecture

## Overview

Real-time telemetry system for monitoring agent activity, resource usage, and LLM interactions during task execution.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Dashboard UI                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Agent Card  │  │  Agent Card  │  │  Agent Card  │      │
│  │  - CPU: 12%  │  │  - CPU: 8%   │  │  - CPU: 5%   │      │
│  │  - Mem: 256MB│  │  - Mem: 180MB│  │  - Mem: 150MB│      │
│  │  - Tokens: 4K│  │  - Tokens: 2K│  │  - Tokens: 1K│      │
│  │  - Activity  │  │  - Activity  │  │  - Activity  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                           ▲
                           │ WebSocket
                           │
┌──────────────────────────┴──────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │            WebSocket Connection Manager                 │ │
│  │  - Team subscriptions                                   │ │
│  │  - Telemetry broadcasting                               │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │            Telemetry Collection Service                 │ │
│  │  - Process metrics collector (CPU/Memory)               │ │
│  │  - Git activity monitor                                 │ │
│  │  - LLM token usage tracker                              │ │
│  │  - Activity log buffer                                  │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                           ▲
                           │ stdout/stderr pipes
                           │
┌──────────────────────────┴──────────────────────────────────┐
│              Orchestrator Subprocess (per team)              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  CrewAI Orchestrator with Git Tools                     │ │
│  │  - Instrumented LLM calls (token tracking)              │ │
│  │  - Git operation logging                                │ │
│  │  - stdout/stderr activity streams                       │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Data Models

### Telemetry Message Types

```typescript
// Process metrics
type ProcessMetrics = {
  pid: number
  cpu_percent: number      // CPU usage percentage
  memory_mb: number         // Memory usage in MB
  threads: number          // Active thread count
  status: string           // Process status
}

// Git activity
type GitActivity = {
  operation: string        // "branch_create" | "commit" | "checkout" | "merge"
  branch: string          // Branch name
  message?: string        // Commit message
  files_changed?: number  // Number of files affected
}

// LLM token usage
type TokenUsage = {
  model: string           // Model ID
  input_tokens: number    // Prompt tokens
  output_tokens: number   // Response tokens
  total_tokens: number    // Sum of input + output
  cost_usd: number       // Estimated cost
}

// Activity log entry
type ActivityLog = {
  timestamp: string       // ISO timestamp
  level: string          // "info" | "warning" | "error"
  message: string        // Log message
  source: string         // "orchestrator" | "git" | "llm" | "system"
}

// Agent telemetry (aggregated)
type AgentTelemetry = {
  agent_id: string
  team_id: string
  process_metrics: ProcessMetrics
  git_activities: GitActivity[]     // Last 10 activities
  token_usage: TokenUsage            // Cumulative
  activity_logs: ActivityLog[]       // Last 50 logs
  last_updated: string               // ISO timestamp
}
```

### WebSocket Message Format

```json
{
  "type": "agent_telemetry",
  "agent_id": "uuid",
  "team_id": "uuid",
  "event": "metrics_update" | "git_activity" | "llm_call" | "log_entry",
  "data": { /* telemetry data */ },
  "timestamp": 1234567890.123
}
```

## Components

### 1. Process Metrics Collector

**File:** `api/app/services/telemetry_service.py`

**Responsibilities:**
- Monitor orchestrator subprocess via PID
- Collect CPU/memory stats every 2 seconds
- Track process lifecycle (started, running, stopped, error)

**Implementation:**
```python
import psutil
import asyncio

class ProcessMetricsCollector:
    def __init__(self, pid: int):
        self.pid = pid
        self.process = psutil.Process(pid)

    async def collect_metrics(self) -> ProcessMetrics:
        return {
            "pid": self.pid,
            "cpu_percent": self.process.cpu_percent(interval=0.1),
            "memory_mb": self.process.memory_info().rss / (1024 * 1024),
            "threads": self.process.num_threads(),
            "status": self.process.status()
        }
```

### 2. Git Activity Monitor

**Approach:** Parse stdout from orchestrator for git tool executions

**Pattern Recognition:**
- `Creating branch: feature/xyz` → git_activity
- `Committed changes: 5 files` → git_activity
- `Switched to branch: xyz` → git_activity

**Implementation:**
```python
class GitActivityMonitor:
    GIT_PATTERNS = {
        r'Creating branch: (.+)': 'branch_create',
        r'Committed (.+) files?': 'commit',
        r'Switched to branch: (.+)': 'checkout'
    }

    def parse_log_line(self, line: str) -> Optional[GitActivity]:
        for pattern, operation in self.GIT_PATTERNS.items():
            match = re.match(pattern, line)
            if match:
                return GitActivity(operation=operation, ...)
        return None
```

### 3. LLM Token Usage Tracker

**Approach 1:** Parse CrewAI output for token usage logs
**Approach 2:** Wrap Anthropic client with usage interceptor

**Implementation (Approach 1 - simpler):**
```python
class TokenUsageTracker:
    TOKEN_PATTERN = r'Token usage: (\d+) input, (\d+) output'

    def parse_token_usage(self, line: str) -> Optional[TokenUsage]:
        match = re.match(self.TOKEN_PATTERN, line)
        if match:
            input_tokens = int(match.group(1))
            output_tokens = int(match.group(2))
            return TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                cost_usd=self.estimate_cost(input_tokens, output_tokens)
            )
        return None
```

### 4. Activity Log Buffer

**Responsibilities:**
- Capture stdout/stderr from orchestrator
- Parse for structured events (git, llm, errors)
- Maintain rolling buffer (last 100 lines)
- Broadcast to WebSocket

**Implementation:**
```python
class ActivityLogBuffer:
    def __init__(self, max_size: int = 100):
        self.logs = []
        self.max_size = max_size

    def add_log(self, level: str, message: str, source: str):
        log = ActivityLog(
            timestamp=datetime.now(UTC).isoformat(),
            level=level,
            message=message,
            source=source
        )
        self.logs.append(log)
        if len(self.logs) > self.max_size:
            self.logs.pop(0)
```

### 5. Telemetry Service

**File:** `api/app/services/telemetry_service.py`

**Main Service:**
```python
class TelemetryService:
    def __init__(self):
        self.active_monitors: Dict[str, AgentMonitor] = {}

    def start_monitoring(self, team_id: str, agent_id: str, pid: int):
        """Start monitoring an agent's orchestrator process"""
        monitor = AgentMonitor(team_id, agent_id, pid)
        self.active_monitors[agent_id] = monitor
        asyncio.create_task(monitor.run())

    def stop_monitoring(self, agent_id: str):
        """Stop monitoring an agent"""
        if agent_id in self.active_monitors:
            self.active_monitors[agent_id].stop()
            del self.active_monitors[agent_id]

class AgentMonitor:
    def __init__(self, team_id: str, agent_id: str, pid: int):
        self.team_id = team_id
        self.agent_id = agent_id
        self.metrics_collector = ProcessMetricsCollector(pid)
        self.git_monitor = GitActivityMonitor()
        self.token_tracker = TokenUsageTracker()
        self.activity_buffer = ActivityLogBuffer()
        self.running = False

    async def run(self):
        """Main monitoring loop"""
        self.running = True
        while self.running:
            # Collect metrics every 2 seconds
            metrics = await self.metrics_collector.collect_metrics()

            # Broadcast telemetry update
            await notify_agent_telemetry(
                self.agent_id,
                self.team_id,
                "metrics_update",
                {"process_metrics": metrics}
            )

            await asyncio.sleep(2)
```

## Integration Points

### 1. Orchestrator Service (`orchestrator_service.py`)

**Changes needed:**
```python
def start_team(self, team_id: UUID, db: Session) -> dict:
    # ... existing code ...

    # Start the orchestrator process
    process = subprocess.Popen(...)

    # NEW: Start telemetry monitoring
    from ..services.telemetry_service import get_telemetry_service
    telemetry = get_telemetry_service()
    for agent in team.agents:
        telemetry.start_monitoring(
            team_id=str(team_id),
            agent_id=str(agent.id),
            pid=process.pid
        )

    # ... rest of code ...
```

### 2. WebSocket Module (`websocket.py`)

**New function:**
```python
async def notify_agent_telemetry(
    agent_id: str,
    team_id: str,
    event: str,
    data: dict
):
    """Broadcast agent telemetry updates"""
    message = {
        "type": "agent_telemetry",
        "agent_id": agent_id,
        "team_id": team_id,
        "event": event,
        "data": data,
        "timestamp": asyncio.get_event_loop().time()
    }
    await manager.send_to_team(team_id, message)
```

### 3. Dashboard UI Components

**New React Component:** `dashboard/components/AgentTelemetryCard.tsx`

```typescript
interface AgentTelemetryCardProps {
  agent: Agent
  telemetry: AgentTelemetry
}

export function AgentTelemetryCard({ agent, telemetry }: Props) {
  return (
    <Card>
      <CardHeader>
        <h3>{agent.name}</h3>
        <Badge>{agent.status}</Badge>
      </CardHeader>
      <CardContent>
        {/* Process Metrics */}
        <MetricsSection>
          <Metric label="CPU" value={`${telemetry.process_metrics.cpu_percent}%`} />
          <Metric label="Memory" value={`${telemetry.process_metrics.memory_mb}MB`} />
          <Metric label="Threads" value={telemetry.process_metrics.threads} />
        </MetricsSection>

        {/* Token Usage */}
        <TokenSection>
          <Metric label="Tokens" value={telemetry.token_usage.total_tokens} />
          <Metric label="Cost" value={`$${telemetry.token_usage.cost_usd.toFixed(4)}`} />
        </TokenSection>

        {/* Recent Activity */}
        <ActivityLog logs={telemetry.activity_logs.slice(-10)} />
      </CardContent>
    </Card>
  )
}
```

## Implementation Phases

### Phase 1: Core Infrastructure (Current)
- ✅ Add psutil to requirements
- ✅ Create telemetry_service.py with ProcessMetricsCollector
- ✅ Integrate with orchestrator_service.py
- ✅ Add WebSocket telemetry broadcasting

### Phase 2: Activity Parsing
- Parse stdout/stderr for git activities
- Parse stdout/stderr for LLM token usage
- Implement activity log buffer

### Phase 3: UI Components
- Create AgentTelemetryCard component
- Add real-time WebSocket connection
- Display metrics, token usage, and activity logs

### Phase 4: Enhanced Features
- Historical metrics (store in DB)
- Cost tracking and alerts
- Performance graphs
- Export telemetry data

## Testing Plan

1. **Unit Tests:**
   - ProcessMetricsCollector with mock process
   - Git activity pattern matching
   - Token usage parsing

2. **Integration Tests:**
   - Start team → telemetry starts
   - WebSocket receives updates
   - Stop team → telemetry stops

3. **End-to-End Test:**
   - Run actual task with monitoring
   - Verify UI displays metrics
   - Verify all telemetry types captured

## Performance Considerations

- **Metrics Collection:** 2-second interval (configurable)
- **WebSocket Throttling:** Max 1 update per second per agent
- **Activity Buffer:** Rolling buffer of 100 entries
- **Memory Usage:** ~1MB per monitored agent
