"use client";

import { Run, AgentTelemetry, cancelRun } from "@/lib/api";
import TaskCard from "./TaskCard";

interface RunExecutionViewProps {
  run: Run;
  taskTelemetry: Record<string, AgentTelemetry>;
  onCancel?: () => void;
  isConnected?: boolean;
}

export default function RunExecutionView({
  run,
  taskTelemetry,
  onCancel,
  isConnected = false,
}: RunExecutionViewProps) {
  const getRunStatusColor = (status: string) => {
    switch (status) {
      case "running":
        return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200";
      case "merging":
        return "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200";
      case "completed":
        return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
      case "pending":
        return "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200";
      case "failed":
      case "cancelled":
        return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
      default:
        return "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200";
    }
  };

  const handleCancel = async () => {
    try {
      await cancelRun(run.id);
      onCancel?.();
    } catch (error) {
      console.error("Failed to cancel run:", error);
    }
  };

  const completedTasks = run.tasks.filter((t) => t.status === "completed").length;
  const failedTasks = run.tasks.filter((t) => t.status === "failed").length;
  const runningTasks = run.tasks.filter((t) => t.status === "running").length;
  const pendingTasks = run.tasks.filter((t) => t.status === "pending").length;

  const isActive = ["pending", "running", "merging"].includes(run.status);

  return (
    <div className="space-y-6">
      {/* Run Header */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="flex justify-between items-start">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                Run Session
              </h2>
              <span
                className={`px-3 py-1 rounded-full text-sm font-medium ${getRunStatusColor(
                  run.status
                )}`}
              >
                {run.status}
              </span>
              {isActive && (
                <div className="flex items-center gap-2">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      isConnected ? "bg-green-500 animate-pulse" : "bg-gray-400"
                    }`}
                  />
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {isConnected ? "Live" : "Reconnecting..."}
                  </span>
                </div>
              )}
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400 font-mono">
              Session: {run.session_id}
            </p>
            {run.integration_branch && (
              <p className="text-sm text-gray-600 dark:text-gray-400 font-mono mt-1">
                Integration branch: {run.integration_branch}
              </p>
            )}
          </div>

          <div className="flex items-center gap-3">
            {isActive && (
              <button
                onClick={handleCancel}
                className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md text-sm font-medium"
              >
                Cancel Run
              </button>
            )}
          </div>
        </div>

        {/* Progress Stats */}
        <div className="mt-6 grid grid-cols-4 gap-4">
          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {run.tasks.length}
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">Total Tasks</div>
          </div>
          <div className="bg-blue-50 dark:bg-blue-900/30 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {runningTasks}
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">Running</div>
          </div>
          <div className="bg-green-50 dark:bg-green-900/30 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">
              {completedTasks}
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">Completed</div>
          </div>
          <div className="bg-red-50 dark:bg-red-900/30 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-red-600 dark:text-red-400">
              {failedTasks}
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">Failed</div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mt-4">
          <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div className="h-full flex">
              <div
                className="bg-green-500 transition-all duration-300"
                style={{ width: `${(completedTasks / run.tasks.length) * 100}%` }}
              />
              <div
                className="bg-blue-500 transition-all duration-300"
                style={{ width: `${(runningTasks / run.tasks.length) * 100}%` }}
              />
              <div
                className="bg-red-500 transition-all duration-300"
                style={{ width: `${(failedTasks / run.tasks.length) * 100}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Merge Phase Status */}
      {run.status === "merging" && (
        <div className="bg-purple-50 dark:bg-purple-900/30 border border-purple-200 dark:border-purple-800 rounded-lg p-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-purple-500 flex items-center justify-center">
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-purple-800 dark:text-purple-200">
                Merge Phase Active
              </h3>
              <p className="text-sm text-purple-600 dark:text-purple-400">
                Resolver agent is merging completed tasks into {run.integration_branch}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Completion Banner */}
      {run.status === "completed" && (
        <div className="bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-green-500 flex items-center justify-center text-white text-xl">
                V
              </div>
              <div>
                <h3 className="text-lg font-semibold text-green-800 dark:text-green-200">
                  Run Completed Successfully
                </h3>
                <p className="text-sm text-green-600 dark:text-green-400">
                  Integration branch <code className="font-mono">{run.integration_branch}</code> is ready to push
                </p>
              </div>
            </div>
            <div className="text-sm text-green-600 dark:text-green-400">
              Completed {run.completed_at && new Date(run.completed_at).toLocaleString()}
            </div>
          </div>
        </div>
      )}

      {/* Failure Banner */}
      {run.status === "failed" && (
        <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg p-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-red-500 flex items-center justify-center text-white text-xl">
              X
            </div>
            <div>
              <h3 className="text-lg font-semibold text-red-800 dark:text-red-200">
                Run Failed
              </h3>
              {run.error_message && (
                <p className="text-sm text-red-600 dark:text-red-400">
                  {run.error_message}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Task Cards Grid */}
      <div>
        <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
          Tasks ({run.tasks.length})
        </h3>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {run.tasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              telemetry={task.agent_name ? taskTelemetry[task.agent_name] : null}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
