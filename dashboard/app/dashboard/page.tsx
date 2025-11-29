"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getTeams, getWorkItems, type Team, type WorkItem } from "@/lib/api";

export default function DashboardPage() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [workItems, setWorkItems] = useState<WorkItem[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      const [teamsData, workItemsData] = await Promise.all([
        getTeams(),
        getWorkItems(),
      ]);
      setTeams(teamsData);
      setWorkItems(workItemsData);
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
        <div className="grid md:grid-cols-3 gap-6 mb-8">
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
      </main>
    </div>
  );
}
