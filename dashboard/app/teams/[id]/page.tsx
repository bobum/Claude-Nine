"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  getTeamFull,
  startTeam,
  stopTeam,
  pauseTeam,
  deleteTeam,
  addAgentToTeam,
  type TeamWithWorkQueue,
} from "@/lib/api";

export default function TeamDetailPage() {
  const params = useParams();
  const router = useRouter();
  const teamId = params.id as string;

  const [team, setTeam] = useState<TeamWithWorkQueue | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [showAddAgent, setShowAddAgent] = useState(false);
  const [newAgent, setNewAgent] = useState({ name: "", role: "", goal: "" });

  const loadTeam = async () => {
    try {
      const data = await getTeamFull(teamId);
      setTeam(data);
      setLoading(false);
    } catch (error) {
      console.error("Failed to load team:", error);
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTeam();
    // Refresh every 5 seconds for live updates
    const interval = setInterval(loadTeam, 5000);
    return () => clearInterval(interval);
  }, [teamId]);

  const handleAction = async (
    action: "start" | "stop" | "pause" | "delete"
  ) => {
    setActionLoading(true);
    try {
      if (action === "start") await startTeam(teamId);
      else if (action === "stop") await stopTeam(teamId);
      else if (action === "pause") await pauseTeam(teamId);
      else if (action === "delete") {
        await deleteTeam(teamId);
        router.push("/teams");
        return;
      }
      await loadTeam();
    } catch (error) {
      console.error(`Failed to ${action} team:`, error);
    }
    setActionLoading(false);
  };

  const handleAddAgent = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await addAgentToTeam(teamId, newAgent);
      setNewAgent({ name: "", role: "", goal: "" });
      setShowAddAgent(false);
      await loadTeam();
    } catch (error) {
      console.error("Failed to add agent:", error);
    }
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
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
          <p className="mt-4 text-gray-600">Loading team...</p>
        </div>
      </div>
    );
  }

  if (!team) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-semibold mb-2">Team not found</h2>
          <Link href="/teams" className="text-blue-600 hover:text-blue-800">
            Back to Teams
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
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
            {team.status === "stopped" && (
              <button
                onClick={() => handleAction("start")}
                disabled={actionLoading}
                className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-md text-sm font-medium disabled:opacity-50"
              >
                Start
              </button>
            )}
            {team.status === "active" && (
              <>
                <button
                  onClick={() => handleAction("pause")}
                  disabled={actionLoading}
                  className="bg-yellow-600 hover:bg-yellow-700 px-4 py-2 rounded-md text-sm font-medium disabled:opacity-50"
                >
                  Pause
                </button>
                <button
                  onClick={() => handleAction("stop")}
                  disabled={actionLoading}
                  className="bg-gray-600 hover:bg-gray-700 px-4 py-2 rounded-md text-sm font-medium disabled:opacity-50"
                >
                  Stop
                </button>
              </>
            )}
            {team.status === "paused" && (
              <button
                onClick={() => handleAction("start")}
                disabled={actionLoading}
                className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-md text-sm font-medium disabled:opacity-50"
              >
                Resume
              </button>
            )}
            <button
              onClick={() => handleAction("delete")}
              disabled={actionLoading}
              className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded-md text-sm font-medium disabled:opacity-50"
            >
              Delete
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-8 px-6">
        {/* Team Info */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                {team.name}
              </h1>
              <p className="text-gray-600 mb-4">{team.product}</p>
              <div className="flex gap-4 text-sm text-gray-500">
                <span>📁 {team.repo_path}</span>
                <span>🌿 {team.main_branch}</span>
              </div>
            </div>
            <span
              className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(
                team.status
              )}`}
            >
              {team.status}
            </span>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          {/* Agents */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">
                Agents ({team.agents.length})
              </h2>
              <button
                onClick={() => setShowAddAgent(!showAddAgent)}
                className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm font-medium"
              >
                + Add Agent
              </button>
            </div>

            {showAddAgent && (
              <form onSubmit={handleAddAgent} className="mb-4 p-4 bg-gray-50 rounded">
                <div className="space-y-3">
                  <input
                    type="text"
                    placeholder="Agent name"
                    required
                    value={newAgent.name}
                    onChange={(e) =>
                      setNewAgent({ ...newAgent, name: e.target.value })
                    }
                    className="w-full px-3 py-2 border rounded"
                  />
                  <input
                    type="text"
                    placeholder="Role"
                    required
                    value={newAgent.role}
                    onChange={(e) =>
                      setNewAgent({ ...newAgent, role: e.target.value })
                    }
                    className="w-full px-3 py-2 border rounded"
                  />
                  <input
                    type="text"
                    placeholder="Goal (optional)"
                    value={newAgent.goal}
                    onChange={(e) =>
                      setNewAgent({ ...newAgent, goal: e.target.value })
                    }
                    className="w-full px-3 py-2 border rounded"
                  />
                  <div className="flex gap-2">
                    <button
                      type="submit"
                      className="flex-1 bg-blue-600 text-white px-3 py-2 rounded text-sm"
                    >
                      Add
                    </button>
                    <button
                      type="button"
                      onClick={() => setShowAddAgent(false)}
                      className="flex-1 bg-gray-300 text-gray-700 px-3 py-2 rounded text-sm"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </form>
            )}

            {team.agents.length === 0 ? (
              <p className="text-gray-500 text-center py-8">No agents yet</p>
            ) : (
              <div className="space-y-3">
                {team.agents.map((agent) => (
                  <div
                    key={agent.id}
                    className="border rounded p-4 hover:bg-gray-50"
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <h3 className="font-semibold">{agent.name}</h3>
                        <p className="text-sm text-gray-600">{agent.role}</p>
                      </div>
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(
                          agent.status
                        )}`}
                      >
                        {agent.status}
                      </span>
                    </div>
                    {agent.goal && (
                      <p className="text-sm text-gray-500 mb-2">{agent.goal}</p>
                    )}
                    {agent.current_branch && (
                      <p className="text-xs text-gray-400">
                        🌿 {agent.current_branch}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Work Queue */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">
              Work Queue ({team.work_items.length})
            </h2>
            {team.work_items.length === 0 ? (
              <p className="text-gray-500 text-center py-8">No work items</p>
            ) : (
              <div className="space-y-3">
                {team.work_items.map((item) => (
                  <div
                    key={item.id}
                    className="border rounded p-4 hover:bg-gray-50"
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex-1">
                        <span className="text-xs text-gray-500">
                          {item.source} #{item.external_id}
                        </span>
                        <h3 className="font-semibold">{item.title}</h3>
                      </div>
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(
                          item.status
                        )}`}
                      >
                        {item.status}
                      </span>
                    </div>
                    {item.description && (
                      <p className="text-sm text-gray-600 mb-2">
                        {item.description.substring(0, 100)}...
                      </p>
                    )}
                    <div className="flex gap-4 text-xs text-gray-500">
                      {item.priority !== null && (
                        <span>Priority: {item.priority}</span>
                      )}
                      {item.story_points && (
                        <span>Points: {item.story_points}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
