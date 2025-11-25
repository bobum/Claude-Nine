"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getTeams, getWorkItems, getAgents, type Team, type WorkItem, type Agent } from "@/lib/api";

export default function DashboardPage() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [workItems, setWorkItems] = useState<WorkItem[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      const [teamsData, workItemsData, agentsData] = await Promise.all([
        getTeams(),
        getWorkItems(),
        getAgents(),
      ]);
      setTeams(teamsData);
      setWorkItems(workItemsData);
      setAgents(agentsData);
      setLoading(false);
    } catch (error) {
      console.error("Failed to load dashboard data:", error);
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // Refresh every 5 seconds
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  const activeTeams = teams.filter((t) => t.status === "active").length;
  const workingAgents = agents.filter((a) => a.status === "working").length;
  const inProgressItems = workItems.filter((w) => w.status === "in_progress").length;
  const completedToday = workItems.filter(
    (w) =>
      w.completed_at &&
      new Date(w.completed_at).toDateString() === new Date().toDateString()
  ).length;

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
          <p className="mt-4 text-gray-600">Loading dashboard...</p>
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
            <span className="text-lg">Dashboard</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-8 px-6">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-2">
            Real-time overview of all your development teams
          </p>
        </div>

        {/* Metrics */}
        <div className="grid md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-500 text-sm">Active Teams</span>
              <div className="text-2xl">👥</div>
            </div>
            <p className="text-3xl font-bold text-gray-900">
              {activeTeams}/{teams.length}
            </p>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-500 text-sm">Working Agents</span>
              <div className="text-2xl">🤖</div>
            </div>
            <p className="text-3xl font-bold text-gray-900">
              {workingAgents}/{agents.length}
            </p>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-500 text-sm">In Progress</span>
              <div className="text-2xl">⚡</div>
            </div>
            <p className="text-3xl font-bold text-gray-900">{inProgressItems}</p>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-500 text-sm">Completed Today</span>
              <div className="text-2xl">✅</div>
            </div>
            <p className="text-3xl font-bold text-gray-900">{completedToday}</p>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          {/* Active Teams */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Active Teams</h2>
            {teams.filter((t) => t.status === "active").length === 0 ? (
              <p className="text-gray-500 text-center py-8">No active teams</p>
            ) : (
              <div className="space-y-3">
                {teams
                  .filter((t) => t.status === "active")
                  .map((team) => {
                    const teamAgents = agents.filter((a) => a.team_id === team.id);
                    const teamWorkItems = workItems.filter((w) => w.team_id === team.id && w.status === "in_progress");
                    return (
                      <Link
                        key={team.id}
                        href={`/teams/${team.id}`}
                        className="block border rounded p-4 hover:bg-gray-50"
                      >
                        <h3 className="font-semibold text-gray-900">{team.name}</h3>
                        <p className="text-sm text-gray-600">{team.product}</p>
                        <div className="flex gap-4 mt-2 text-xs text-gray-500">
                          <span>{teamAgents.length} agents</span>
                          <span>{teamWorkItems.length} active items</span>
                        </div>
                      </Link>
                    );
                  })}
              </div>
            )}
          </div>

          {/* Recent Activity */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Recent Activity</h2>
            {workItems.length === 0 ? (
              <p className="text-gray-500 text-center py-8">No activity yet</p>
            ) : (
              <div className="space-y-3">
                {workItems
                  .filter((w) => w.status === "in_progress" || w.status === "pr_ready")
                  .slice(0, 5)
                  .map((item) => (
                    <div key={item.id} className="border-l-4 border-blue-500 pl-4 py-2">
                      <div className="flex justify-between items-start">
                        <div>
                          <p className="font-semibold text-sm">{item.title}</p>
                          <p className="text-xs text-gray-500">
                            {item.source} #{item.external_id}
                          </p>
                        </div>
                        <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                          {item.status.replace("_", " ")}
                        </span>
                      </div>
                    </div>
                  ))}
              </div>
            )}
          </div>
        </div>

        {/* All Agents Status */}
        <div className="bg-white rounded-lg shadow p-6 mt-6">
          <h2 className="text-xl font-semibold mb-4">
            All Agents ({agents.length})
          </h2>
          <div className="grid md:grid-cols-3 lg:grid-cols-4 gap-4">
            {agents.map((agent) => {
              const team = teams.find((t) => t.id === agent.team_id);
              const statusColors = {
                working: "border-blue-500 bg-blue-50",
                idle: "border-gray-300 bg-gray-50",
                blocked: "border-red-500 bg-red-50",
                error: "border-red-500 bg-red-50",
              };
              return (
                <div
                  key={agent.id}
                  className={`border-2 rounded-lg p-4 ${
                    statusColors[agent.status] || statusColors.idle
                  }`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="font-semibold text-sm">{agent.name}</h3>
                    <span
                      className={`w-2 h-2 rounded-full ${
                        agent.status === "working"
                          ? "bg-blue-500"
                          : agent.status === "blocked" || agent.status === "error"
                          ? "bg-red-500"
                          : "bg-gray-400"
                      }`}
                    />
                  </div>
                  <p className="text-xs text-gray-600 mb-1">{agent.role}</p>
                  {team && (
                    <p className="text-xs text-gray-500">Team: {team.name}</p>
                  )}
                  {agent.current_branch && (
                    <p className="text-xs text-gray-400 mt-1">
                      🌿 {agent.current_branch}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </main>
    </div>
  );
}
