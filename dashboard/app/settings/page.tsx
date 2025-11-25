"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ThemeToggle from "@/components/ThemeToggle";
import TutorialSettings from "@/components/TutorialSettings";
import Toast from "@/components/Toast";
import { useToast } from "@/lib/hooks";

interface Settings {
  anthropic_api_key?: string;
  azure_devops_url?: string;
  azure_devops_token?: string;
  azure_devops_organization?: string;
  jira_url?: string;
  jira_email?: string;
  jira_api_token?: string;
  github_token?: string;
  linear_api_key?: string;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const { toasts, removeToast, success, error } = useToast();

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const response = await fetch("http://localhost:8000/api/settings");
      if (response.ok) {
        const data = await response.json();
        setSettings(data);
      }
    } catch (err) {
      console.error("Failed to load settings:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await fetch("http://localhost:8000/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });

      if (response.ok) {
        success("Settings saved successfully!");
      } else {
        error("Failed to save settings");
      }
    } catch (err) {
      error("Failed to save settings");
      console.error("Save error:", err);
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async (integration: string) => {
    try {
      const response = await fetch(
        `http://localhost:8000/api/settings/test/${integration}`,
        { method: "POST" }
      );

      if (response.ok) {
        success(`${integration} connection successful!`);
      } else {
        const data = await response.json();
        error(`${integration} connection failed: ${data.detail || "Unknown error"}`);
      }
    } catch (err) {
      error(`Failed to test ${integration} connection`);
    }
  };

  const toggleShowKey = (key: string) => {
    setShowKeys((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const maskValue = (value: string | undefined, key: string) => {
    if (!value) return "";
    if (showKeys[key]) return value;
    return "•".repeat(Math.min(value.length, 40));
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-400">Loading settings...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="bg-gray-900 text-white py-4 px-6 shadow-md">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-2xl font-bold hover:text-gray-300">
              Claude-Nine
            </Link>
            <span className="text-gray-400">/</span>
            <span className="text-lg">Settings</span>
          </div>
          <div className="flex items-center gap-4">
            <ThemeToggle />
            <TutorialSettings />
          </div>
        </div>
      </header>

      <Toast toasts={toasts} onRemove={removeToast} />

      <main className="max-w-4xl mx-auto py-8 px-6">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
            Settings & Integrations
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            Configure API keys and integration credentials
          </p>
        </div>

        <div className="space-y-6">
          {/* Anthropic API Key */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                  Anthropic API Key
                </h2>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  Required for Claude AI agents
                </p>
              </div>
              <span className="px-3 py-1 bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 text-xs font-medium rounded-full">
                Required
              </span>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  API Key
                </label>
                <div className="flex gap-2">
                  <input
                    type={showKeys["anthropic"] ? "text" : "password"}
                    value={settings.anthropic_api_key || ""}
                    onChange={(e) =>
                      setSettings({ ...settings, anthropic_api_key: e.target.value })
                    }
                    placeholder="sk-ant-api03-..."
                    className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  />
                  <button
                    onClick={() => toggleShowKey("anthropic")}
                    className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
                  >
                    {showKeys["anthropic"] ? "Hide" : "Show"}
                  </button>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Get your API key from{" "}
                  <a
                    href="https://console.anthropic.com/settings/keys"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    console.anthropic.com
                  </a>
                </p>
              </div>
            </div>
          </div>

          {/* Azure DevOps */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                  Azure DevOps
                </h2>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  Sync work items from Azure DevOps
                </p>
              </div>
              <button
                onClick={() => handleTestConnection("azure_devops")}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg"
              >
                Test Connection
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Organization URL
                </label>
                <input
                  type="text"
                  value={settings.azure_devops_url || ""}
                  onChange={(e) =>
                    setSettings({ ...settings, azure_devops_url: e.target.value })
                  }
                  placeholder="https://dev.azure.com/your-org"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Organization Name
                </label>
                <input
                  type="text"
                  value={settings.azure_devops_organization || ""}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      azure_devops_organization: e.target.value,
                    })
                  }
                  placeholder="your-organization"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Personal Access Token (PAT)
                </label>
                <div className="flex gap-2">
                  <input
                    type={showKeys["ado"] ? "text" : "password"}
                    value={settings.azure_devops_token || ""}
                    onChange={(e) =>
                      setSettings({ ...settings, azure_devops_token: e.target.value })
                    }
                    placeholder="••••••••••••••••"
                    className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  />
                  <button
                    onClick={() => toggleShowKey("ado")}
                    className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
                  >
                    {showKeys["ado"] ? "Hide" : "Show"}
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Jira */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                  Jira
                </h2>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  Sync issues from Jira
                </p>
              </div>
              <button
                onClick={() => handleTestConnection("jira")}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg"
              >
                Test Connection
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Jira URL
                </label>
                <input
                  type="text"
                  value={settings.jira_url || ""}
                  onChange={(e) =>
                    setSettings({ ...settings, jira_url: e.target.value })
                  }
                  placeholder="https://your-domain.atlassian.net"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Email
                </label>
                <input
                  type="email"
                  value={settings.jira_email || ""}
                  onChange={(e) =>
                    setSettings({ ...settings, jira_email: e.target.value })
                  }
                  placeholder="you@company.com"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  API Token
                </label>
                <div className="flex gap-2">
                  <input
                    type={showKeys["jira"] ? "text" : "password"}
                    value={settings.jira_api_token || ""}
                    onChange={(e) =>
                      setSettings({ ...settings, jira_api_token: e.target.value })
                    }
                    placeholder="••••••••••••••••"
                    className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  />
                  <button
                    onClick={() => toggleShowKey("jira")}
                    className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
                  >
                    {showKeys["jira"] ? "Hide" : "Show"}
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* GitHub */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                  GitHub
                </h2>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  Sync issues from GitHub repositories
                </p>
              </div>
              <button
                onClick={() => handleTestConnection("github")}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg"
              >
                Test Connection
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Personal Access Token
                </label>
                <div className="flex gap-2">
                  <input
                    type={showKeys["github"] ? "text" : "password"}
                    value={settings.github_token || ""}
                    onChange={(e) =>
                      setSettings({ ...settings, github_token: e.target.value })
                    }
                    placeholder="ghp_••••••••••••••••"
                    className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  />
                  <button
                    onClick={() => toggleShowKey("github")}
                    className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
                  >
                    {showKeys["github"] ? "Hide" : "Show"}
                  </button>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Required scopes: repo, read:org
                </p>
              </div>
            </div>
          </div>

          {/* Linear */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                  Linear
                </h2>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  Sync issues from Linear
                </p>
              </div>
              <button
                onClick={() => handleTestConnection("linear")}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg"
              >
                Test Connection
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  API Key
                </label>
                <div className="flex gap-2">
                  <input
                    type={showKeys["linear"] ? "text" : "password"}
                    value={settings.linear_api_key || ""}
                    onChange={(e) =>
                      setSettings({ ...settings, linear_api_key: e.target.value })
                    }
                    placeholder="lin_api_••••••••••••••••"
                    className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  />
                  <button
                    onClick={() => toggleShowKey("linear")}
                    className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
                  >
                    {showKeys["linear"] ? "Hide" : "Show"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div className="mt-8 flex justify-end gap-4">
          <Link
            href="/"
            className="px-6 py-3 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
          >
            Cancel
          </Link>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg font-medium"
          >
            {saving ? "Saving..." : "Save Settings"}
          </button>
        </div>
      </main>
    </div>
  );
}
