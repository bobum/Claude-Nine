"use client";

import { RunTask, AgentTelemetry } from "@/lib/api";

interface TaskCardProps {
  task: RunTask;
  telemetry: AgentTelemetry | null;
}

export default function TaskCard({ task, telemetry }: TaskCardProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case "running":
        return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200";
      case "completed":
        return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
      case "pending":
        return "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200";
      case "failed":
      case "retrying":
        return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
      default:
        return "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200";
    }
  };

  const getLogLevelColor = (level: string) => {
    switch (level) {
      case "error":
        return "text-red-600 dark:text-red-400";
      case "warning":
        return "text-yellow-600 dark:text-yellow-400";
      default:
        return "text-gray-600 dark:text-gray-400";
    }
  };

  const workItem = task.work_item;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 hover:shadow-xl transition-shadow">
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-purple-500 flex items-center justify-center text-white font-bold text-lg">
            {task.agent_name ? task.agent_name.charAt(0) : "T"}
          </div>
          <div>
            <h3 className="font-bold text-lg text-gray-900 dark:text-gray-100">
              {workItem?.title || `Task ${task.id.substring(0, 8)}`}
            </h3>
            {task.agent_name && (
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Agent: {task.agent_name}
              </p>
            )}
            {task.branch_name && (
              <p className="text-xs text-gray-500 dark:text-gray-500 mt-1 font-mono">
                {task.branch_name}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {task.status === "running" && (
            <div className="flex items-center gap-1 px-2 py-1 bg-green-100 dark:bg-green-900 rounded-full">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-xs font-medium text-green-700 dark:text-green-300">LIVE</span>
            </div>
          )}
          <span
            className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(task.status)}`}
          >
            {task.status}
          </span>
        </div>
      </div>

      {/* Work Item Info */}
      {workItem && (
        <div className="mb-4 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-gray-500 dark:text-gray-400">
              {workItem.source} #{workItem.external_id}
            </span>
            {workItem.priority !== null && (
              <span className="px-2 py-0.5 bg-gray-200 dark:bg-gray-600 rounded text-xs">
                P{workItem.priority}
              </span>
            )}
          </div>
          {workItem.description && (
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-2 line-clamp-2">
              {workItem.description}
            </p>
          )}
        </div>
      )}

      {/* Process Metrics */}
      {telemetry && telemetry.process_metrics && (
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
            <div className="flex items-center gap-2">
              <span className="text-2xl">CPU</span>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400">Usage</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  {telemetry.process_metrics.cpu_percent.toFixed(1)}%
                </p>
              </div>
            </div>
          </div>

          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
            <div className="flex items-center gap-2">
              <span className="text-2xl">RAM</span>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400">Memory</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  {telemetry.process_metrics.memory_mb.toFixed(0)}MB
                </p>
              </div>
            </div>
          </div>

          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
            <div className="flex items-center gap-2">
              <span className="text-2xl">TKN</span>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400">Tokens</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  {telemetry.token_usage.total_tokens.toLocaleString()}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
            <div className="flex items-center gap-2">
              <span className="text-2xl">$</span>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400">Cost</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  ${((telemetry.token_usage.input_tokens / 1_000_000 * 3.00) + (telemetry.token_usage.output_tokens / 1_000_000 * 15.00)).toFixed(4)}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Git Activities */}
      {telemetry && telemetry.git_activities.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
            Git Activity
          </h4>
          <div className="space-y-2 max-h-32 overflow-y-auto">
            {telemetry.git_activities.slice(0, 5).map((activity, idx) => (
              <div
                key={idx}
                className="text-xs p-2 bg-gray-50 dark:bg-gray-700 rounded flex items-center gap-2"
              >
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {activity.operation}
                </span>
                {activity.branch && (
                  <span className="text-gray-600 dark:text-gray-400 font-mono">
                    {activity.branch}
                  </span>
                )}
                {activity.message && (
                  <span className="text-gray-500 dark:text-gray-400 truncate">
                    {activity.message}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Activity Logs */}
      {telemetry && telemetry.activity_logs.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
            Activity Feed
          </h4>
          <div className="space-y-1 max-h-24 overflow-y-auto text-xs">
            {telemetry.activity_logs.slice(-5).reverse().map((log, idx) => (
              <div
                key={idx}
                className={`p-2 rounded ${getLogLevelColor(log.level)} bg-gray-50 dark:bg-gray-700`}
              >
                <span className="font-mono text-gray-500 dark:text-gray-400">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>{" "}
                <span className="truncate">{log.message.substring(0, 60)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error message */}
      {task.error_message && (
        <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg">
          <h4 className="text-sm font-semibold text-red-700 dark:text-red-400 mb-1">Error</h4>
          <p className="text-sm text-red-600 dark:text-red-300">{task.error_message}</p>
        </div>
      )}

      {/* Completion Results */}
      {task.status === "completed" && workItem && (
        <div className="mt-4 p-3 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-lg">
          <h4 className="text-sm font-semibold text-green-700 dark:text-green-400 mb-2">Completed</h4>
          <div className="grid grid-cols-2 gap-2 text-sm">
            {workItem.commits_count !== null && (
              <div>
                <span className="text-gray-500 dark:text-gray-400">Commits:</span>{" "}
                <span className="font-medium text-gray-900 dark:text-gray-100">{workItem.commits_count}</span>
              </div>
            )}
            {workItem.files_changed_count !== null && (
              <div>
                <span className="text-gray-500 dark:text-gray-400">Files:</span>{" "}
                <span className="font-medium text-gray-900 dark:text-gray-100">{workItem.files_changed_count}</span>
              </div>
            )}
          </div>
          {task.branch_name && (
            <p className="mt-2 text-xs font-mono text-green-600 dark:text-green-400">
              Branch: {task.branch_name}
            </p>
          )}
        </div>
      )}

      {/* Waiting state */}
      {task.status === "pending" && (
        <div className="text-center py-4 text-gray-500 dark:text-gray-400">
          <p className="text-sm">Waiting to start...</p>
        </div>
      )}

      {/* Running without telemetry */}
      {task.status === "running" && !telemetry && (
        <div className="text-center py-4 text-gray-500 dark:text-gray-400">
          <p className="text-sm">Waiting for telemetry data...</p>
          <div className="inline-block mt-2 h-4 w-4 animate-spin rounded-full border-2 border-solid border-blue-600 border-r-transparent"></div>
        </div>
      )}
    </div>
  );
}
