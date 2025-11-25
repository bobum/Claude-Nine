"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ThemeToggle from "@/components/ThemeToggle";
import TutorialSettings from "@/components/TutorialSettings";
import Tooltip from "@/components/Tooltip";
import Toast from "@/components/Toast";
import { useToast, useWebSocket } from "@/lib/hooks";
import { useTutorial, homeTutorialSteps } from "@/components/Tutorial";

interface HealthStatus {
  status: string;
  version?: string;
  service?: string;
}

export default function Home() {
  const [apiHealth, setApiHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const { toasts, removeToast, success } = useToast();
  const { isConnected } = useWebSocket("ws://localhost:8000/ws");
  const { startTutorial } = useTutorial();

  useEffect(() => {
    fetch("http://localhost:8000/health")
      .then((res) => res.json())
      .then((data) => {
        setApiHealth(data);
        setLoading(false);
      })
      .catch((error) => {
        console.error("API health check failed:", error);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (isConnected) {
      success("Connected to real-time updates");
    }
  }, [isConnected, success]);

  // Start tutorial on first visit
  useEffect(() => {
    const completed = localStorage.getItem("claude-nine-tutorial-completed");
    if (!completed) {
      // Delay to ensure page is fully rendered
      const timer = setTimeout(() => {
        startTutorial(homeTutorialSteps);
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [startTutorial]);

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-gray-900 text-white py-4 px-6 shadow-md">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <h1 className="text-2xl font-bold">Claude-Nine</h1>
          <div className="flex items-center gap-4">
            <Tooltip content="WebSocket connection status - green when connected to real-time updates">
              <div className="flex items-center gap-2">
                <div
                  className={`w-2 h-2 rounded-full ${
                    isConnected ? "bg-green-500 animate-pulse" : "bg-gray-500"
                  }`}
                />
                <span className="text-sm">
                  {isConnected ? "Live" : "Connecting..."}
                </span>
              </div>
            </Tooltip>
            <Tooltip content="Backend API health status">
              <div className="flex items-center gap-2">
                <div
                  className={`w-2 h-2 rounded-full ${
                    apiHealth?.status === "ok" ? "bg-green-500" : "bg-red-500"
                  }`}
                />
                <span className="text-sm">
                  API {loading ? "Checking..." : apiHealth?.status || "Offline"}
                </span>
              </div>
            </Tooltip>
            <div data-tour="theme-toggle">
              <ThemeToggle />
            </div>
            <Tooltip content="Configure API keys and integrations">
              <Link
                href="/settings"
                className="text-white hover:text-gray-300 transition-colors"
              >
                <span className="text-2xl">⚙️</span>
              </Link>
            </Tooltip>
            <TutorialSettings />
          </div>
        </div>
      </header>

      <Toast toasts={toasts} onRemove={removeToast} />

      <main className="flex-1 bg-gray-50 dark:bg-gray-900">
        <div className="max-w-7xl mx-auto py-12 px-6">
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-4">
              Dev Team in a Box
            </h2>
            <p className="text-xl text-gray-600 dark:text-gray-400 mb-8">
              Manage multiple AI development teams from a single dashboard
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6 mb-12">
            <div
              data-tour="team-management"
              className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 hover:shadow-lg transition-shadow"
            >
              <div className="text-3xl mb-4">👥</div>
              <h3 className="text-xl font-semibold mb-2 text-gray-900 dark:text-gray-100">
                Team Management
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                Create and manage multiple development teams with custom agents
              </p>
              <Tooltip content="Click to view and manage all your teams" position="bottom">
                <Link
                  href="/teams"
                  className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 font-medium"
                >
                  View Teams →
                </Link>
              </Tooltip>
            </div>

            <div
              data-tour="work-queue"
              className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 hover:shadow-lg transition-shadow"
            >
              <div className="text-3xl mb-4">📋</div>
              <h3 className="text-xl font-semibold mb-2 text-gray-900 dark:text-gray-100">
                Work Queue
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                Assign work items from Azure DevOps, Jira, or GitHub
              </p>
              <Tooltip content="Manage work items and bulk assign to teams" position="bottom">
                <Link
                  href="/work-items"
                  className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 font-medium"
                >
                  View Work Items →
                </Link>
              </Tooltip>
            </div>

            <div
              data-tour="monitoring"
              className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 hover:shadow-lg transition-shadow"
            >
              <div className="text-3xl mb-4">📊</div>
              <h3 className="text-xl font-semibold mb-2 text-gray-900 dark:text-gray-100">
                Real-time Monitoring
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                Monitor agent activity, commits, and conflicts in real-time
              </p>
              <Tooltip content="View metrics and monitor agent activity" position="bottom">
                <Link
                  href="/dashboard"
                  className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 font-medium"
                >
                  View Dashboard →
                </Link>
              </Tooltip>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-8">
            <h3 className="text-2xl font-semibold mb-4 text-gray-900 dark:text-gray-100">
              Quick Start
            </h3>
            <ol className="space-y-3 text-gray-700 dark:text-gray-300">
              <li className="flex items-start">
                <span className="font-semibold mr-2">1.</span>
                <span>
                  <Link
                    href="/settings"
                    className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
                  >
                    Configure your API keys
                  </Link>{" "}
                  for Anthropic and integrations
                </span>
              </li>
              <li className="flex items-start">
                <span className="font-semibold mr-2">2.</span>
                <span>
                  <Link
                    href="/teams/new"
                    className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
                  >
                    Create your first team
                  </Link>{" "}
                  and add agents
                </span>
              </li>
              <li className="flex items-start">
                <span className="font-semibold mr-2">3.</span>
                <span>Connect to Azure DevOps, Jira, or GitHub via Settings</span>
              </li>
              <li className="flex items-start">
                <span className="font-semibold mr-2">4.</span>
                <span>Assign work items to teams</span>
              </li>
              <li className="flex items-start">
                <span className="font-semibold mr-2">5.</span>
                <span>Start the team and watch your AI developers work!</span>
              </li>
            </ol>
          </div>
        </div>
      </main>

      <footer className="bg-gray-900 text-white py-6 px-6">
        <div className="max-w-7xl mx-auto text-center">
          <p className="text-sm text-gray-400">
            Claude-Nine - AI Development Teams Orchestration Platform
          </p>
          <p className="text-xs text-gray-500 mt-2">
            Version 1.0.0 | Working in harmony
          </p>
        </div>
      </footer>
    </div>
  );
}
