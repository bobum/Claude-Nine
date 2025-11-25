"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getWorkItems, getTeams, createWorkItem, type WorkItem, type Team } from "@/lib/api";

export default function WorkItemsPage() {
  const [workItems, setWorkItems] = useState<WorkItem[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [filters, setFilters] = useState({
    status: "",
    source: "",
    team_id: "",
  });
  const [newItem, setNewItem] = useState({
    external_id: "",
    source: "manual" as const,
    title: "",
    description: "",
    priority: 0,
    team_id: "",
  });

  const loadData = async () => {
    try {
      const [items, teamsData] = await Promise.all([
        getWorkItems(filters.status || filters.source || filters.team_id ? filters : undefined),
        getTeams(),
      ]);
      setWorkItems(items);
      setTeams(teamsData);
      setLoading(false);
    } catch (error) {
      console.error("Failed to load data:", error);
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [filters]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createWorkItem(newItem);
      setNewItem({
        external_id: "",
        source: "manual",
        title: "",
        description: "",
        priority: 0,
        team_id: "",
      });
      setShowCreate(false);
      await loadData();
    } catch (error) {
      console.error("Failed to create work item:", error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-green-100 text-green-800";
      case "in_progress":
        return "bg-blue-100 text-blue-800";
      case "pr_ready":
        return "bg-purple-100 text-purple-800";
      case "queued":
        return "bg-gray-100 text-gray-800";
      case "blocked":
        return "bg-red-100 text-red-800";
      case "cancelled":
        return "bg-gray-100 text-gray-500";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const getSourceBadge = (source: string) => {
    const colors: Record<string, string> = {
      azure_devops: "bg-blue-100 text-blue-800",
      jira: "bg-indigo-100 text-indigo-800",
      github: "bg-gray-800 text-white",
      linear: "bg-purple-100 text-purple-800",
      manual: "bg-gray-100 text-gray-800",
    };
    return colors[source] || colors.manual;
  };

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
            <span className="text-lg">Work Items</span>
          </div>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-md text-sm font-medium"
          >
            + New Work Item
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-8 px-6">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Work Items</h1>
          <p className="text-gray-600 mt-2">
            Manage work items from Azure DevOps, Jira, GitHub, and more
          </p>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="grid md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Status
              </label>
              <select
                value={filters.status}
                onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="">All Statuses</option>
                <option value="queued">Queued</option>
                <option value="in_progress">In Progress</option>
                <option value="pr_ready">PR Ready</option>
                <option value="completed">Completed</option>
                <option value="blocked">Blocked</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Source
              </label>
              <select
                value={filters.source}
                onChange={(e) => setFilters({ ...filters, source: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="">All Sources</option>
                <option value="azure_devops">Azure DevOps</option>
                <option value="jira">Jira</option>
                <option value="github">GitHub</option>
                <option value="linear">Linear</option>
                <option value="manual">Manual</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Team
              </label>
              <select
                value={filters.team_id}
                onChange={(e) => setFilters({ ...filters, team_id: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="">All Teams</option>
                {teams.map((team) => (
                  <option key={team.id} value={team.id}>
                    {team.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Create Form */}
        {showCreate && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4">Create Work Item</h2>
            <form onSubmit={handleCreate}>
              <div className="grid md:grid-cols-2 gap-4 mb-4">
                <input
                  type="text"
                  placeholder="External ID (e.g., PBI-123)"
                  required
                  value={newItem.external_id}
                  onChange={(e) =>
                    setNewItem({ ...newItem, external_id: e.target.value })
                  }
                  className="px-3 py-2 border rounded"
                />
                <select
                  value={newItem.source}
                  onChange={(e) =>
                    setNewItem({ ...newItem, source: e.target.value as any })
                  }
                  className="px-3 py-2 border rounded"
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
                value={newItem.title}
                onChange={(e) =>
                  setNewItem({ ...newItem, title: e.target.value })
                }
                className="w-full px-3 py-2 border rounded mb-4"
              />
              <textarea
                placeholder="Description"
                value={newItem.description}
                onChange={(e) =>
                  setNewItem({ ...newItem, description: e.target.value })
                }
                className="w-full px-3 py-2 border rounded mb-4"
                rows={3}
              />
              <div className="grid md:grid-cols-2 gap-4 mb-4">
                <input
                  type="number"
                  placeholder="Priority"
                  value={newItem.priority}
                  onChange={(e) =>
                    setNewItem({ ...newItem, priority: parseInt(e.target.value) })
                  }
                  className="px-3 py-2 border rounded"
                />
                <select
                  value={newItem.team_id}
                  onChange={(e) =>
                    setNewItem({ ...newItem, team_id: e.target.value })
                  }
                  className="px-3 py-2 border rounded"
                >
                  <option value="">Unassigned</option>
                  {teams.map((team) => (
                    <option key={team.id} value={team.id}>
                      {team.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex gap-2">
                <button
                  type="submit"
                  className="flex-1 bg-blue-600 text-white px-4 py-2 rounded font-medium"
                >
                  Create
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreate(false)}
                  className="flex-1 bg-gray-300 text-gray-700 px-4 py-2 rounded font-medium"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Work Items List */}
        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
            <p className="mt-4 text-gray-600">Loading work items...</p>
          </div>
        ) : workItems.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <div className="text-6xl mb-4">📋</div>
            <h2 className="text-2xl font-semibold mb-2">No work items yet</h2>
            <p className="text-gray-600 mb-6">
              Create a work item or connect to Azure DevOps/Jira
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {workItems.map((item) => (
              <div key={item.id} className="bg-white rounded-lg shadow p-6">
                <div className="flex justify-between items-start mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${getSourceBadge(
                          item.source
                        )}`}
                      >
                        {item.source.toUpperCase()}
                      </span>
                      <span className="text-sm text-gray-500">
                        #{item.external_id}
                      </span>
                    </div>
                    <h3 className="text-xl font-semibold text-gray-900">
                      {item.title}
                    </h3>
                  </div>
                  <span
                    className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(
                      item.status
                    )}`}
                  >
                    {item.status.replace("_", " ")}
                  </span>
                </div>
                {item.description && (
                  <p className="text-gray-600 mb-3">{item.description}</p>
                )}
                <div className="flex gap-6 text-sm text-gray-500">
                  {item.priority !== null && <span>Priority: {item.priority}</span>}
                  {item.story_points && <span>Points: {item.story_points}</span>}
                  {item.team_id && (
                    <span>
                      Team: {teams.find((t) => t.id === item.team_id)?.name || "Unknown"}
                    </span>
                  )}
                  <span>Created: {new Date(item.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
