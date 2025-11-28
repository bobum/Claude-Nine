"use client";

import { Agent, AgentTelemetry } from "@/lib/api";

interface AgentTelemetryCardProps {
  agent: Agent;
  telemetry: AgentTelemetry | null;
}

export default function AgentTelemetryCard({
  agent,
  telemetry,
}: AgentTelemetryCardProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case "working":
        return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200";
      case "idle":
        return "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200";
      case "blocked":
      case "error":
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

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 hover:shadow-xl transition-shadow">
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-blue-500 flex items-center justify-center text-white font-bold text-lg">
            {agent.name.charAt(0)}
          </div>
          <div>
            <h3 className="font-bold text-lg text-gray-900 dark:text-gray-100">
              {agent.name}
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {agent.role}
            </p>
            {telemetry && telemetry.timestamp && (
              <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                Last update: {new Date(telemetry.timestamp).toLocaleTimeString()}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {telemetry && (
            <div className="flex items-center gap-1 px-2 py-1 bg-green-100 dark:bg-green-900 rounded-full">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-xs font-medium text-green-700 dark:text-green-300">LIVE</span>
            </div>
          )}
          <span
            className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(
              agent.status
            )}`}
          >
            {agent.status}
          </span>
        </div>
      </div>

      {/* Process Metrics */}
      {telemetry && telemetry.process_metrics && (
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
            <div className="flex items-center gap-2">
              <span className="text-2xl">💻</span>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400">CPU</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  {telemetry.process_metrics.cpu_percent.toFixed(1)}%
                </p>
              </div>
            </div>
          </div>

          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
            <div className="flex items-center gap-2">
              <span className="text-2xl">🧠</span>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400">RAM</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  {telemetry.process_metrics.memory_mb.toFixed(0)}MB
                </p>
              </div>
            </div>
          </div>

          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
            <div className="flex items-center gap-2">
              <span className="text-2xl">🪙</span>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Tokens
                </p>
                <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  {telemetry.token_usage.total_tokens.toLocaleString()}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
            <div className="flex items-center gap-2">
              <span className="text-2xl">💵</span>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400">Cost</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  ${telemetry.token_usage.cost_usd.toFixed(4)}
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
            Recent Git Activity
          </h4>
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {telemetry.git_activities.slice(0, 5).map((activity, idx) => (
              <div
                key={idx}
                className="text-xs p-2 bg-gray-50 dark:bg-gray-700 rounded flex items-center gap-2"
              >
                <span>
                  {activity.operation === "commit" && "📝"}
                  {activity.operation === "branch_create" && "🌿"}
                  {activity.operation === "checkout" && "↔️"}
                  {activity.operation === "merge" && "🔀"}
                </span>
                <div className="flex-1">
                  <span className="font-medium text-gray-900 dark:text-gray-100">
                    {activity.operation}
                  </span>
                  {activity.branch && (
                    <span className="text-gray-600 dark:text-gray-400">
                      {" "}
                      on {activity.branch}
                    </span>
                  )}
                  {activity.message && (
                    <p className="text-gray-500 dark:text-gray-400 truncate">
                      {activity.message}
                    </p>
                  )}
                </div>
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
          <div className="space-y-1 max-h-32 overflow-y-auto text-xs">
            {telemetry.activity_logs.slice(-10).reverse().map((log, idx) => (
              <div
                key={idx}
                className={`p-2 rounded ${getLogLevelColor(log.level)} bg-gray-50 dark:bg-gray-700`}
              >
                <span className="font-mono text-gray-500 dark:text-gray-400">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>{" "}
                <span className="truncate">{log.message.substring(0, 80)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* No telemetry placeholder */}
      {!telemetry && (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <p className="text-sm">Waiting for telemetry data...</p>
          <div className="inline-block mt-2 h-4 w-4 animate-spin rounded-full border-2 border-solid border-blue-600 border-r-transparent"></div>
        </div>
      )}
    </div>
  );
}
