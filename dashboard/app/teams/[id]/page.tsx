"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  getTeamFull,
  getTeamReadiness,
  getRuns,
  getRun,
  createRun,
  deleteTeam,
  createWorkItem,
  type TeamWithWorkQueue,
  type TeamReadiness,
  type AgentTelemetry,
  type Run,
  type WorkItem,
} from "@/lib/api";
import { useWebSocket } from "@/lib/hooks";
import RunExecutionView from "@/components/RunExecutionView";

export default function TeamDetailPage() {
  const params = useParams();
  const router = useRouter();
  const teamId = params.id as string;

  const [team, setTeam] = useState<TeamWithWorkQueue | null>(null);
  const [readiness, setReadiness] = useState<TeamReadiness | null>(null);
  const [activeRun, setActiveRun] = useState<Run | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [taskTelemetry, setTaskTelemetry] = useState<Record<string, AgentTelemetry>>({});
  const [showAddWorkItem, setShowAddWorkItem] = useState(false);
  const [expandedWorkItem, setExpandedWorkItem] = useState<string | null>(null);
  const [selectedWorkItems, setSelectedWorkItems] = useState<Set<string>>(new Set());
  const [newWorkItem, setNewWorkItem] = useState({
    external_id: "",
    source: "manual" as const,
    title: "",
    description: "",
    priority: 0,
    team_id: teamId,
  });

  // WebSocket connection for real-time telemetry
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";
  const { lastMessage, isConnected } = useWebSocket(wsUrl);

  const loadTeam = useCallback(async () => {
    try {
      const data = await getTeamFull(teamId);
      setTeam(data);

      // Load readiness status
      const readinessData = await getTeamReadiness(teamId);
      setReadiness(readinessData);

      // Check for active runs
      const runs = await getRuns({ team_id: teamId, status: "running", limit: 1 });
      if (runs.length > 0) {
        const fullRun = await getRun(runs[0].id);
        setActiveRun(fullRun);
      } else {
        // Check for pending or merging runs too
        const pendingRuns = await getRuns({ team_id: teamId, status: "pending", limit: 1 });
        if (pendingRuns.length > 0) {
          const fullRun = await getRun(pendingRuns[0].id);
          setActiveRun(fullRun);
        } else {
          const mergingRuns = await getRuns({ team_id: teamId, status: "merging", limit: 1 });
          if (mergingRuns.length > 0) {
            const fullRun = await getRun(mergingRuns[0].id);
            setActiveRun(fullRun);
          } else {
            setActiveRun(null);
          }
        }
      }

      setLoading(false);
    } catch (error) {
      console.error("Failed to load team:", error);
      setLoading(false);
    }
  }, [teamId]);

  useEffect(() => {
    loadTeam();
    // Refresh every 3 seconds for live updates
    const interval = setInterval(loadTeam, 3000);
    return () => clearInterval(interval);
  }, [loadTeam]);

  // Handle WebSocket messages for telemetry and status updates
    useEffect(() => {
      if (lastMessage) {
        const message = lastMessage;
        console.log('[WebSocket] Received message:', message.type, message);

        // Handle telemetry updates
        if (message.type === "agent_telemetry" && message.team_id === teamId) {
          const telemetryData = message.data as AgentTelemetry;
          console.log('[Telemetry] Received telemetry for agent:', telemetryData.agent_name);
          setTaskTelemetry((prev) => ({
            ...prev,
            [telemetryData.agent_name]: telemetryData,
          }));
        }

        // Handle work item status updates - update activeRun tasks in real-time
        if (message.type === "work_item_update") {
          const workItemData = message.data as WorkItem;
          console.log('[WorkItem] Status update:', workItemData.id, workItemData.status);

          // Update the task status in activeRun if this work item is in our run
          setActiveRun((prev) => {
            if (!prev) return prev;
            const updatedTasks = prev.tasks.map((task) => {
              if (task.work_item_id === workItemData.id) {
                // Map work item status to task status
                let taskStatus = task.status;
                if (workItemData.status === "in_progress") taskStatus = "running";
                else if (workItemData.status === "completed" || workItemData.status === "pr_ready") taskStatus = "completed";
                else if (workItemData.status === "blocked" || workItemData.status === "cancelled") taskStatus = "failed";
                return {
                  ...task,
                  status: taskStatus,
                  work_item: { ...task.work_item, ...workItemData } as typeof task.work_item,
                };
              }
              return task;
            });
            return { ...prev, tasks: updatedTasks };
          });
        }

        // Handle run status updates
        if (message.type === "run_status_update" && message.data?.id === activeRun?.id) {
          console.log('[Run] Status update:', message.data.status);
          setActiveRun((prev) => prev ? { ...prev, status: message.data.status } : prev);
        }
      }
    }, [lastMessage, teamId, activeRun?.id]);

  const handleDeleteTeam = async () => {
    if (!confirm("Are you sure you want to delete this team?")) return;

    setActionLoading(true);
    try {
      await deleteTeam(teamId);
      router.push("/teams");
    } catch (error) {
      console.error("Failed to delete team:", error);
    }
    setActionLoading(false);
  };

  const handleStartRun = async () => {
    if (selectedWorkItems.size === 0) {
      alert("Please select at least one work item to start a run");
      return;
    }

    const maxTasks = team?.max_concurrent_tasks || 4;
    if (maxTasks > 0 && selectedWorkItems.size > maxTasks) {
      alert(`You can only run up to ${maxTasks} tasks concurrently. Please select fewer items.`);
      return;
    }

    setActionLoading(true);
    try {
      const sessionId = `${Date.now().toString(36)}`;
      const run = await createRun({
        team_id: teamId,
        session_id: sessionId,
        selected_work_item_ids: Array.from(selectedWorkItems),
        dry_run: true,  // Always use dry-run for now to avoid API costs
      });
      setActiveRun(run);
      setSelectedWorkItems(new Set());
      await loadTeam();
    } catch (error) {
      console.error("Failed to start run:", error);
    }
    setActionLoading(false);
  };

  const handleAddWorkItem = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createWorkItem({ ...newWorkItem, team_id: teamId });
      setNewWorkItem({
        external_id: "",
        source: "manual",
        title: "",
        description: "",
        priority: 0,
        team_id: teamId,
      });
      setShowAddWorkItem(false);
      await loadTeam();
    } catch (error) {
      console.error("Failed to add work item:", error);
    }
  };

  const toggleWorkItemSelection = (itemId: string) => {
    setSelectedWorkItems((prev) => {
      const next = new Set(prev);
      if (next.has(itemId)) {
        next.delete(itemId);
      } else {
        next.add(itemId);
      }
      return next;
    });
  };

  const selectAllQueued = () => {
    const queuedItems = team?.work_items.filter((item) => item.status === "queued") || [];
    const maxTasks = team?.max_concurrent_tasks || 4;
    const itemsToSelect = maxTasks > 0 ? queuedItems.slice(0, maxTasks) : queuedItems;
    setSelectedWorkItems(new Set(itemsToSelect.map((item) => item.id)));
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "active":
        return "bg-green-100 text-green-800";
      case "working":
        return "bg-blue-100 text-blue-800";
      case "paused":
        return "bg-yellow-100 text-yellow-800";
      case "stopped":
      case "idle":
        return "bg-gray-100 text-gray-800";
      case "error":
      case "blocked":
        return "bg-red-100 text-red-800";
      case "queued":
        return "bg-blue-100 text-blue-800";
      case "in_progress":
        return "bg-yellow-100 text-yellow-800";
      case "completed":
      case "pr_ready":
        return "bg-green-100 text-green-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const queuedWorkItems = team?.work_items.filter((item) => item.status === "queued") || [];
  const completedWorkItems = team?.work_items.filter((item) =>
    item.status === "completed" || item.status === "pr_ready"
  ) || [];
  const inProgressWorkItems = team?.work_items.filter((item) => item.status === "in_progress") || [];

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-400">Loading team...</p>
        </div>
      </div>
    );
  }

  if (!team) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-2">Team not found</h2>
          <Link href="/teams" className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300">
            Back to Teams
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-gray-900 text-white py-4 px-6 shadow-md">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-2xl font-bold hover:text-gray-300">
              Claude-Nine
            </Link>
            <span className="text-gray-400">/</span>
            <Link href="/teams" className="hover:text-gray-300">
              Teams
            </Link>
            <span className="text-gray-400">/</span>
            <span className="text-lg">{team.name}</span>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleDeleteTeam}
              disabled={actionLoading || !!activeRun}
              className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded-md text-sm font-medium disabled:opacity-50"
            >
              Delete Team
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-8 px-6">
        {/* Team Info */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-6">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                {team.name}
              </h1>
              <p className="text-gray-600 dark:text-gray-400 mb-4">{team.product}</p>
              <div className="flex gap-4 text-sm text-gray-500 dark:text-gray-400">
                <span>Repo: {team.repo_path}</span>
                <span>Branch: {team.main_branch}</span>
                <span>Max concurrent: {team.max_concurrent_tasks || 4}</span>
              </div>
            </div>
            <span
              className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(team.status)}`}
            >
              {team.status}
            </span>
          </div>
        </div>

        {/* Active Run View */}
        {activeRun && (
          <div className="mb-6">
            <RunExecutionView
              run={activeRun}
              taskTelemetry={taskTelemetry}
              onCancel={loadTeam}
              isConnected={isConnected}
            />
          </div>
        )}

        {/* Work Queue - Show when no active run */}
        {!activeRun && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-6">
            <div className="flex justify-between items-center mb-4">
              <div>
                <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                  Work Queue ({queuedWorkItems.length} queued)
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  Select work items to start a run (max: {team.max_concurrent_tasks || 4})
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={selectAllQueued}
                  className="bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 px-3 py-1 rounded text-sm font-medium"
                >
                  Select All (up to max)
                </button>
                <button
                  onClick={() => setShowAddWorkItem(!showAddWorkItem)}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm font-medium"
                >
                  + Add Work Item
                </button>
              </div>
            </div>

            {/* Start Run Button */}
            {selectedWorkItems.size > 0 && (
              <div className="mb-4 p-4 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-lg flex justify-between items-center">
                <div>
                  <p className="font-medium text-green-800 dark:text-green-200">
                    {selectedWorkItems.size} item(s) selected
                  </p>
                  <p className="text-sm text-green-600 dark:text-green-400">
                    Ready to start a new run
                  </p>
                </div>
                <button
                  onClick={handleStartRun}
                  disabled={actionLoading || !readiness?.is_ready}
                  className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded-md font-medium disabled:opacity-50"
                >
                  {actionLoading ? "Starting..." : "Start Run"}
                </button>
              </div>
            )}

            {/* Readiness Check */}
            {readiness && !readiness.is_ready && (
              <div className="mb-4 p-4 bg-yellow-50 dark:bg-yellow-900/30 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                <h3 className="font-medium text-yellow-800 dark:text-yellow-200 mb-2">
                  Cannot start run
                </h3>
                <ul className="text-sm text-yellow-600 dark:text-yellow-400 space-y-1">
                  {readiness.issues.map((issue, idx) => (
                    <li key={idx}>- {issue}</li>
                  ))}
                </ul>
              </div>
            )}

            {showAddWorkItem && (
              <form onSubmit={handleAddWorkItem} className="mb-4 p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <div className="space-y-3">
                  <div className="grid md:grid-cols-2 gap-3">
                    <input
                      type="text"
                      placeholder="External ID (e.g., PBI-123)"
                      required
                      value={newWorkItem.external_id}
                      onChange={(e) =>
                        setNewWorkItem({ ...newWorkItem, external_id: e.target.value })
                      }
                      className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                    />
                    <select
                      value={newWorkItem.source}
                      onChange={(e) =>
                        setNewWorkItem({ ...newWorkItem, source: e.target.value as any })
                      }
                      className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                    >
                      <option value="manual">Manual</option>
                      <option value="azure_devops">Azure DevOps</option>
                      <option value="jira">Jira</option>
                      <option value="github">GitHub</option>
                      <option value="linear">Linear</option>
                    </select>
                  </div>
                  <input
                    type="text"
                    placeholder="Title"
                    required
                    value={newWorkItem.title}
                    onChange={(e) =>
                      setNewWorkItem({ ...newWorkItem, title: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  />
                  <textarea
                    placeholder="Description"
                    value={newWorkItem.description}
                    onChange={(e) =>
                      setNewWorkItem({ ...newWorkItem, description: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                    rows={3}
                  />
                  <input
                    type="number"
                    placeholder="Priority"
                    value={newWorkItem.priority}
                    onChange={(e) =>
                      setNewWorkItem({ ...newWorkItem, priority: parseInt(e.target.value) || 0 })
                    }
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  />
                  <div className="flex gap-2">
                    <button
                      type="submit"
                      className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 rounded-lg text-sm font-medium"
                    >
                      Add
                    </button>
                    <button
                      type="button"
                      onClick={() => setShowAddWorkItem(false)}
                      className="flex-1 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 px-3 py-2 rounded-lg text-sm font-medium"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </form>
            )}

            {/* Queued Work Items */}
            {queuedWorkItems.length === 0 ? (
              <p className="text-gray-500 dark:text-gray-400 text-center py-8">
                No work items in queue. Add some work items to get started.
              </p>
            ) : (
              <div className="space-y-2">
                {queuedWorkItems.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => toggleWorkItemSelection(item.id)}
                    className={`border rounded-lg p-4 cursor-pointer transition-all ${
                      selectedWorkItems.has(item.id)
                        ? "border-green-500 bg-green-50 dark:bg-green-900/30"
                        : "border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700"
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex items-start gap-3">
                        <input
                          type="checkbox"
                          checked={selectedWorkItems.has(item.id)}
                          onChange={() => {}}
                          className="mt-1 h-4 w-4 rounded border-gray-300"
                        />
                        <div>
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            {item.source} #{item.external_id}
                          </span>
                          <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                            {item.title}
                          </h3>
                          {item.description && (
                            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 line-clamp-2">
                              {item.description}
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {item.priority !== null && (
                          <span className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs">
                            P{item.priority}
                          </span>
                        )}
                        <span
                          className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(
                            item.status
                          )}`}
                        >
                          {item.status}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* In Progress Work Items */}
        {inProgressWorkItems.length > 0 && !activeRun && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-6">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
              In Progress ({inProgressWorkItems.length})
            </h2>
            <div className="space-y-2">
              {inProgressWorkItems.map((item) => (
                <div
                  key={item.id}
                  className="border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 bg-yellow-50 dark:bg-yellow-900/20"
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="text-xs text-gray-500">
                        {item.source} #{item.external_id}
                      </span>
                      <h3 className="font-semibold text-gray-900 dark:text-gray-100">{item.title}</h3>
                    </div>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(item.status)}`}>
                      {item.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Completed Work Items */}
        {completedWorkItems.length > 0 && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
              Completed ({completedWorkItems.length})
            </h2>
            <div className="space-y-2">
              {completedWorkItems.map((item) => (
                <div
                  key={item.id}
                  onClick={() => setExpandedWorkItem(expandedWorkItem === item.id ? null : item.id)}
                  className="border border-green-200 dark:border-green-800 rounded-lg p-4 bg-green-50 dark:bg-green-900/20 cursor-pointer"
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="text-xs text-gray-500">
                        {item.source} #{item.external_id}
                      </span>
                      <h3 className="font-semibold text-gray-900 dark:text-gray-100">{item.title}</h3>
                      {expandedWorkItem === item.id && (
                        <div className="mt-3 text-sm text-gray-600 dark:text-gray-400 space-y-2">
                          {item.description && <p>{item.description}</p>}
                          <div className="grid grid-cols-2 gap-2">
                            {item.branch_name && (
                              <div>
                                <span className="font-medium">Branch:</span>{" "}
                                <code className="text-xs">{item.branch_name}</code>
                              </div>
                            )}
                            {item.commits_count !== null && (
                              <div>
                                <span className="font-medium">Commits:</span> {item.commits_count}
                              </div>
                            )}
                            {item.files_changed_count !== null && (
                              <div>
                                <span className="font-medium">Files changed:</span>{" "}
                                {item.files_changed_count}
                              </div>
                            )}
                            {item.pr_url && (
                              <div>
                                <a
                                  href={item.pr_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-blue-600 hover:underline"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  View PR
                                </a>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(item.status)}`}>
                        {item.status}
                      </span>
                      <span className="text-gray-400">
                        {expandedWorkItem === item.id ? "v" : ">"}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
