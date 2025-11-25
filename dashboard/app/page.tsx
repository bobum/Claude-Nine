"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ThemeToggle from "@/components/ThemeToggle";
import Toast from "@/components/Toast";
import { useToast, useWebSocket } from "@/lib/hooks";

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

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-gray-900 text-white py-4 px-6 shadow-md">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <h1 className="text-2xl font-bold">Claude-Nine</h1>
          <div className="flex items-center gap-4">
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
            <ThemeToggle />
          </div>
        </div>
      </header>

      <Toast toasts={toasts} onRemove={removeToast} />

      <main className="flex-1 bg-gray-50">
        <div className="max-w-7xl mx-auto py-12 px-6">
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Dev Team in a Box
            </h2>
            <p className="text-xl text-gray-600 mb-8">
              Manage multiple AI development teams from a single dashboard
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6 mb-12">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-3xl mb-4">👥</div>
              <h3 className="text-xl font-semibold mb-2">Team Management</h3>
              <p className="text-gray-600 mb-4">
                Create and manage multiple development teams with custom agents
              </p>
              <Link
                href="/teams"
                className="text-blue-600 hover:text-blue-800 font-medium"
              >
                View Teams →
              </Link>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-3xl mb-4">📋</div>
              <h3 className="text-xl font-semibold mb-2">Work Queue</h3>
              <p className="text-gray-600 mb-4">
                Assign work items from Azure DevOps, Jira, or GitHub
              </p>
              <Link
                href="/work-items"
                className="text-blue-600 hover:text-blue-800 font-medium"
              >
                View Work Items →
              </Link>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-3xl mb-4">📊</div>
              <h3 className="text-xl font-semibold mb-2">Real-time Monitoring</h3>
              <p className="text-gray-600 mb-4">
                Monitor agent activity, commits, and conflicts in real-time
              </p>
              <Link
                href="/dashboard"
                className="text-blue-600 hover:text-blue-800 font-medium"
              >
                View Dashboard →
              </Link>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-8">
            <h3 className="text-2xl font-semibold mb-4">Quick Start</h3>
            <ol className="space-y-3 text-gray-700">
              <li className="flex items-start">
                <span className="font-semibold mr-2">1.</span>
                <span>
                  <Link
                    href="/teams/new"
                    className="text-blue-600 hover:text-blue-800"
                  >
                    Create your first team
                  </Link>{" "}
                  and add agents
                </span>
              </li>
              <li className="flex items-start">
                <span className="font-semibold mr-2">2.</span>
                <span>Connect to Azure DevOps, Jira, or GitHub</span>
              </li>
              <li className="flex items-start">
                <span className="font-semibold mr-2">3.</span>
                <span>Assign work items to teams</span>
              </li>
              <li className="flex items-start">
                <span className="font-semibold mr-2">4.</span>
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
