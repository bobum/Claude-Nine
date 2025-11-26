"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getWorkItems, getTeams, createWorkItem, bulkAssignWorkItems, type WorkItem, type Team } from "@/lib/api";

export default function WorkItemsPage() {
  const [workItems, setWorkItems] = useState<WorkItem[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [showBulkAssign, setShowBulkAssign] = useState(false);
  const [bulkAssignTeamId, setBulkAssignTeamId] = useState("");
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

  const toggleSelectItem = (itemId: string) => {
    const newSelected = new Set(selectedItems);
    if (newSelected.has(itemId)) {
      newSelected.delete(itemId);
    } else {
      newSelected.add(itemId);
    }
    setSelectedItems(newSelected);
  };

  const toggleSelectAll = () => {
    if (selectedItems.size === workItems.length) {
      setSelectedItems(new Set());
    } else {
      setSelectedItems(new Set(workItems.map(item => item.id)));
    }
  };

  const handleBulkAssign = async () => {
    if (!bulkAssignTeamId || selectedItems.size === 0) return;

    try {
      await bulkAssignWorkItems(Array.from(selectedItems), bulkAssignTeamId);
      setShowBulkAssign(false);
      setBulkAssignTeamId("");
      setSelectedItems(new Set());
      await loadData();
    } catch (error) {
      console.error("Failed to bulk assign:", error);
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
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
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
          <div className="flex gap-2">
            {selectedItems.size > 0 && (
              <button
                onClick={() => setShowBulkAssign(true)}
                className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-md text-sm font-medium"
              >
                Assign {selectedItems.size} Items
              </button>
            )}
            <button
              onClick={() => setShowCreate(!showCreate)}
              className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-md text-sm font-medium"
            >
              + New Work Item
            </button>
          </div>
        </div>
      </header>

      {/* Bulk Assign Modal */}
      {showBulkAssign && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
              Assign {selectedItems.size} Work Items to Team
            </h2>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              Select a team to assign the selected work items to their queue
            </p>
            <select
              value={bulkAssignTeamId}
              onChange={(e) => setBulkAssignTeamId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 mb-4"
            >
              <option value="">Select a team...</option>
              {teams.map((team) => (
                <option key={team.id} value={team.id}>
                  {team.name} - {team.product}
                </option>
              ))}
            </select>
            <div className="flex gap-2">
              <button
                onClick={handleBulkAssign}
                disabled={!bulkAssignTeamId}
                className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg font-medium"
              >
                Assign to Queue
              </button>
              <button
                onClick={() => {
                  setShowBulkAssign(false);
                  setBulkAssignTeamId("");
                }}
                className="flex-1 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 px-4 py-2 rounded-lg font-medium"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-8 px-6">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Work Items</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            Manage work items from Azure DevOps, Jira, GitHub, and more
          </p>
        </div>

        {/* Filters */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 mb-6">
          <div className="grid md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Status
              </label>
              <select
                value={filters.status}
                onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
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
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Source
              </label>
              <select
                value={filters.source}
                onChange={(e) => setFilters({ ...filters, source: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
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
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Team
              </label>
              <select
                value={filters.team_id}
                onChange={(e) => setFilters({ ...filters, team_id: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
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
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-6">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">Create Work Item</h2>
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
                  className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
                <select
                  value={newItem.source}
                  onChange={(e) =>
                    setNewItem({ ...newItem, source: e.target.value as any })
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
                value={newItem.title}
                onChange={(e) =>
                  setNewItem({ ...newItem, title: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 mb-4"
              />
              <textarea
                placeholder="Description"
                value={newItem.description}
                onChange={(e) =>
                  setNewItem({ ...newItem, description: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 mb-4"
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
                  className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
                <select
                  value={newItem.team_id}
                  onChange={(e) =>
                    setNewItem({ ...newItem, team_id: e.target.value })
                  }
                  className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
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
                  className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium"
                >
                  Create
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreate(false)}
                  className="flex-1 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 px-4 py-2 rounded-lg font-medium"
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
          <>
            {/* Select All Bar */}
            {workItems.length > 0 && (
              <div className="bg-white rounded-lg shadow p-4 mb-4 flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={selectedItems.size === workItems.length && workItems.length > 0}
                  onChange={toggleSelectAll}
                  className="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                />
                <span className="font-medium text-gray-700">
                  {selectedItems.size === workItems.length && workItems.length > 0
                    ? `All ${workItems.length} items selected`
                    : selectedItems.size > 0
                    ? `${selectedItems.size} items selected`
                    : "Select all"}
                </span>
                {selectedItems.size > 0 && (
                  <button
                    onClick={() => setSelectedItems(new Set())}
                    className="ml-auto text-sm text-gray-600 hover:text-gray-800"
                  >
                    Clear selection
                  </button>
                )}
              </div>
            )}

            <div className="space-y-4">
              {workItems.map((item) => (
                <div
                  key={item.id}
                  className={`bg-white rounded-lg shadow p-6 transition-all ${
                    selectedItems.has(item.id) ? 'ring-2 ring-blue-500' : ''
                  }`}
                >
                  <div className="flex gap-4">
                    <input
                      type="checkbox"
                      checked={selectedItems.has(item.id)}
                      onChange={() => toggleSelectItem(item.id)}
                      className="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500 mt-1"
                    />
                    <div className="flex-1">
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
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
