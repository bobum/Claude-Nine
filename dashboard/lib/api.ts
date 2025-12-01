// API client for Claude-Nine backend

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Team {
  id: string;
  name: string;
  product: string;
  repo_path: string;
  main_branch: string;
  max_concurrent_tasks: number | null;
  status: "active" | "paused" | "stopped" | "error";
  created_at: string;
  updated_at: string;
}

export interface Agent {
  id: string;
  team_id: string;
  name: string;
  role: string;
  goal: string | null;
  status: "idle" | "working" | "blocked" | "error";
  worktree_path: string | null;
  current_branch: string | null;
  last_activity: string | null;
  created_at: string;
}

export interface WorkItem {
  id: string;
  team_id: string | null;
  external_id: string;
  source: "azure_devops" | "jira" | "github" | "linear" | "manual";
  title: string;
  description: string | null;
  acceptance_criteria: string | null;
  status: "queued" | "in_progress" | "pr_ready" | "completed" | "blocked" | "cancelled";
  priority: number;
  story_points: number | null;
  external_url: string | null;
  assigned_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  // Completion results
  branch_name: string | null;
  commits_count: number | null;
  files_changed_count: number | null;
  pr_url: string | null;
}

export interface TeamWithAgents extends Team {
  agents: Agent[];
}

export interface TeamWithWorkQueue extends Team {
  agents: Agent[];
  work_items: WorkItem[];
}

// Teams
export async function getTeams(): Promise<Team[]> {
  const response = await fetch(`${API_BASE_URL}/api/teams/`);
  if (!response.ok) throw new Error("Failed to fetch teams");
  return response.json();
}

export async function getTeam(id: string): Promise<TeamWithAgents> {
  const response = await fetch(`${API_BASE_URL}/api/teams/${id}`);
  if (!response.ok) throw new Error("Failed to fetch team");
  return response.json();
}

export async function getTeamFull(id: string): Promise<TeamWithWorkQueue> {
  const response = await fetch(`${API_BASE_URL}/api/teams/${id}/full`);
  if (!response.ok) throw new Error("Failed to fetch team");
  return response.json();
}

export interface TeamReadiness {
  team_id: string;
  is_ready: boolean;
  checks: {
    has_repository: boolean;
    repository_exists: boolean;
    is_git_repository: boolean;
    has_queued_work: boolean;
  };
  issues: string[];
  queued_work_count: number;
  queued_work_items: Array<{
    id: string;
    title: string;
    status: string;
    priority: number;
  }>;
}

export async function getTeamReadiness(id: string): Promise<TeamReadiness> {
  const response = await fetch(`${API_BASE_URL}/api/teams/${id}/readiness`);
  if (!response.ok) throw new Error("Failed to fetch team readiness");
  return response.json();
}

// Personas
export interface Persona {
  persona_type: string;
  display_name: string;
  role_template: string;
  goal_template: string;
  backstory_template: string;
  icon: string;
  max_per_team: number | null;
  specializations: string[];
}

export async function getPersonas(): Promise<{ personas: Persona[] }> {
  const response = await fetch(`${API_BASE_URL}/api/personas/`);
  if (!response.ok) throw new Error("Failed to fetch personas");
  return response.json();
}

export async function createTeam(data: {
  name: string;
  product: string;
  repo_path: string;
  main_branch?: string;
}): Promise<Team> {
  const response = await fetch(`${API_BASE_URL}/api/teams/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error("Failed to create team");
  return response.json();
}

export async function startTeam(id: string): Promise<{ message: string }> {
  const response = await fetch(`${API_BASE_URL}/api/teams/${id}/start`, {
    method: "POST",
  });
  if (!response.ok) throw new Error("Failed to start team");
  return response.json();
}

export async function stopTeam(id: string): Promise<{ message: string }> {
  const response = await fetch(`${API_BASE_URL}/api/teams/${id}/stop`, {
    method: "POST",
  });
  if (!response.ok) throw new Error("Failed to stop team");
  return response.json();
}

export async function pauseTeam(id: string): Promise<{ message: string }> {
  const response = await fetch(`${API_BASE_URL}/api/teams/${id}/pause`, {
    method: "POST",
  });
  if (!response.ok) throw new Error("Failed to pause team");
  return response.json();
}

export async function deleteTeam(id: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/teams/${id}`, {
    method: "DELETE",
  });
  if (!response.ok) throw new Error("Failed to delete team");
}

// Work Items
export async function getWorkItems(filters?: {
  team_id?: string;
  status?: string;
  source?: string;
}): Promise<WorkItem[]> {
  const params = new URLSearchParams();
  if (filters?.team_id) params.append("team_id", filters.team_id);
  if (filters?.status) params.append("status", filters.status);
  if (filters?.source) params.append("source", filters.source);

  const url = `${API_BASE_URL}/api/work-items/?${params.toString()}`;
  const response = await fetch(url);
  if (!response.ok) throw new Error("Failed to fetch work items");
  return response.json();
}

export async function createWorkItem(data: {
  external_id: string;
  source: string;
  title: string;
  description?: string;
  acceptance_criteria?: string;
  priority?: number;
  story_points?: number;
  external_url?: string;
  team_id?: string;
}): Promise<WorkItem> {
  const response = await fetch(`${API_BASE_URL}/api/work-items/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error("Failed to create work item");
  return response.json();
}

export async function updateWorkItem(
  id: string,
  data: { team_id?: string; status?: string; priority?: number }
): Promise<WorkItem> {
  const response = await fetch(`${API_BASE_URL}/api/work-items/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error("Failed to update work item");
  return response.json();
}

export async function bulkAssignWorkItems(
  workItemIds: string[],
  teamId: string
): Promise<WorkItem[]> {
  const response = await fetch(`${API_BASE_URL}/api/work-items/bulk-assign`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      work_item_ids: workItemIds,
      team_id: teamId,
    }),
  });
  if (!response.ok) throw new Error("Failed to bulk assign work items");
  return response.json();
}

// Telemetry Types
export interface ProcessMetrics {
  pid: number;
  cpu_percent: number;
  memory_mb: number;
  threads: number;
  status: string;
}

export interface GitActivity {
  operation: string;
  branch?: string | null;
  message?: string | null;
  files_changed?: number | null;
  timestamp?: string | null;
  agent_name?: string | null;
}

export interface TokenUsage {
  model: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost_usd: number;
}

export interface ActivityLog {
  timestamp: string;
  level: string;
  message: string;
  source: string;
  agent_name?: string | null;
}

export interface AgentTelemetry {
  agent_name: string;
  process_metrics: ProcessMetrics;
  token_usage: TokenUsage;
  git_activities: GitActivity[];
  activity_logs: ActivityLog[];
  timestamp: string;
}

// Run Types (orchestrator session tracking)
export type RunStatus = "pending" | "running" | "merging" | "completed" | "failed" | "cancelled";
export type RunTaskStatus = "pending" | "running" | "completed" | "failed" | "retrying";

export interface RunTask {
  id: string;
  run_id: string;
  work_item_id: string | null;
  agent_name: string | null;
  branch_name: string | null;
  worktree_path: string | null;
  status: RunTaskStatus;
  telemetry_data: Record<string, unknown> | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  work_item?: WorkItem;
}

export interface Run {
  id: string;
  team_id: string;
  session_id: string;
  status: RunStatus;
  integration_branch: string | null;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  tasks: RunTask[];
}

// Runs API
export async function getRuns(filters?: {
  team_id?: string;
  status?: RunStatus;
  limit?: number;
}): Promise<Run[]> {
  const params = new URLSearchParams();
  if (filters?.team_id) params.append("team_id", filters.team_id);
  if (filters?.status) params.append("status", filters.status);
  if (filters?.limit) params.append("limit", filters.limit.toString());

  const response = await fetch(`${API_BASE_URL}/api/runs/?${params.toString()}`);
  if (!response.ok) throw new Error("Failed to fetch runs");
  return response.json();
}

export async function createRun(data: {
  team_id: string;
  session_id: string;
  selected_work_item_ids: string[];
}): Promise<Run> {
  const response = await fetch(`${API_BASE_URL}/api/runs/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error("Failed to create run");
  return response.json();
}

export async function getRun(runId: string): Promise<Run> {
  const response = await fetch(`${API_BASE_URL}/api/runs/${runId}`);
  if (!response.ok) throw new Error("Failed to fetch run");
  return response.json();
}

export async function updateRunStatus(
  runId: string,
  status: RunStatus,
  errorMessage?: string
): Promise<Run> {
  const params = new URLSearchParams();
  params.append("status", status);
  if (errorMessage) params.append("error_message", errorMessage);

  const response = await fetch(`${API_BASE_URL}/api/runs/${runId}/status?${params.toString()}`, {
    method: "PATCH",
  });
  if (!response.ok) throw new Error("Failed to update run status");
  return response.json();
}

export async function updateRunTask(
  runId: string,
  taskId: string,
  updates: {
    status?: RunTaskStatus;
    agent_name?: string;
    branch_name?: string;
    worktree_path?: string;
    telemetry_data?: Record<string, unknown>;
    error_message?: string;
  }
): Promise<RunTask> {
  const params = new URLSearchParams();
  if (updates.status) params.append("status", updates.status);
  if (updates.agent_name) params.append("agent_name", updates.agent_name);
  if (updates.branch_name) params.append("branch_name", updates.branch_name);
  if (updates.worktree_path) params.append("worktree_path", updates.worktree_path);
  if (updates.error_message) params.append("error_message", updates.error_message);

  const response = await fetch(`${API_BASE_URL}/api/runs/${runId}/tasks/${taskId}?${params.toString()}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: updates.telemetry_data ? JSON.stringify({ telemetry_data: updates.telemetry_data }) : undefined,
  });
  if (!response.ok) throw new Error("Failed to update run task");
  return response.json();
}

export async function cancelRun(runId: string): Promise<Run> {
  const response = await fetch(`${API_BASE_URL}/api/runs/${runId}/cancel`, {
    method: "POST",
  });
  if (!response.ok) throw new Error("Failed to cancel run");
  return response.json();
}
