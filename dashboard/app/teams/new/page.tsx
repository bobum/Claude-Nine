"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createTeam } from "@/lib/api";

export default function NewTeamPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    name: "",
    product: "",
    repo_path: "",
    main_branch: "main",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await createTeam(formData);
      router.push("/teams");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create team");
      setLoading(false);
    }
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
            <Link href="/teams" className="hover:text-gray-300">
              Teams
            </Link>
            <span className="text-gray-400">/</span>
            <span className="text-lg">New</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-3xl mx-auto py-8 px-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-6">
            Create New Team
          </h1>

          {error && (
            <div className="bg-red-50 dark:bg-red-900 border border-red-200 dark:border-red-700 text-red-700 dark:text-red-200 px-4 py-3 rounded mb-6">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="space-y-6">
              {/* Team Name */}
              <div>
                <label
                  htmlFor="name"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
                >
                  Team Name *
                </label>
                <input
                  type="text"
                  id="name"
                  required
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  placeholder="e.g., E-Commerce Team"
                />
              </div>

              {/* Product */}
              <div>
                <label
                  htmlFor="product"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
                >
                  Product Name *
                </label>
                <input
                  type="text"
                  id="product"
                  required
                  value={formData.product}
                  onChange={(e) =>
                    setFormData({ ...formData, product: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  placeholder="e.g., ShopifyClone"
                />
              </div>

              {/* Repository Path */}
              <div>
                <label
                  htmlFor="repo_path"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
                >
                  Repository Path *
                </label>
                <input
                  type="text"
                  id="repo_path"
                  required
                  value={formData.repo_path}
                  onChange={(e) =>
                    setFormData({ ...formData, repo_path: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  placeholder="e.g., /repos/shopify-clone"
                />
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  Absolute path to the repository directory
                </p>
              </div>

              {/* Main Branch */}
              <div>
                <label
                  htmlFor="main_branch"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
                >
                  Main Branch
                </label>
                <input
                  type="text"
                  id="main_branch"
                  value={formData.main_branch}
                  onChange={(e) =>
                    setFormData({ ...formData, main_branch: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  placeholder="main"
                />
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-4 mt-8">
              <button
                type="submit"
                disabled={loading}
                className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-6 py-3 rounded-lg font-medium"
              >
                {loading ? "Creating..." : "Create Team"}
              </button>
              <Link
                href="/teams"
                className="flex-1 text-center bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 px-6 py-3 rounded-lg font-medium"
              >
                Cancel
              </Link>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}
