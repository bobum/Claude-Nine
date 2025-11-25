"use client";

import { useState } from "react";
import { useTutorial } from "./Tutorial";

export default function TutorialSettings() {
  const [showMenu, setShowMenu] = useState(false);
  const { isTutorialEnabled, toggleTutorial, resetTutorial } = useTutorial();

  return (
    <div className="relative">
      <button
        onClick={() => setShowMenu(!showMenu)}
        className="p-2 rounded-lg hover:bg-gray-700 transition-colors"
        aria-label="Tutorial settings"
        title="Tutorial Settings"
      >
        <span className="text-2xl">❓</span>
      </button>

      {showMenu && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setShowMenu(false)}
          />

          {/* Menu */}
          <div className="absolute right-0 mt-2 w-64 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-50">
            <div className="p-4">
              <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-3">
                Tutorial Settings
              </h3>

              <div className="space-y-3">
                {/* Toggle Tutorial */}
                <div className="flex items-center justify-between">
                  <label
                    htmlFor="tutorial-toggle"
                    className="text-sm text-gray-700 dark:text-gray-300"
                  >
                    Enable Tutorial
                  </label>
                  <button
                    id="tutorial-toggle"
                    onClick={toggleTutorial}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      isTutorialEnabled ? "bg-blue-600" : "bg-gray-300 dark:bg-gray-600"
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        isTutorialEnabled ? "translate-x-6" : "translate-x-1"
                      }`}
                    />
                  </button>
                </div>

                {/* Reset Tutorial */}
                <button
                  onClick={() => {
                    resetTutorial();
                    setShowMenu(false);
                    window.location.reload(); // Reload to restart tutorial
                  }}
                  className="w-full text-left text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
                >
                  🔄 Restart Tutorial
                </button>

                <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    The tutorial guides you through Claude-Nine features. Toggle it off
                    to hide tour popups.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
