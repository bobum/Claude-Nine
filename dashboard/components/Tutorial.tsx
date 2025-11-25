"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import Joyride, { Step, CallBackProps, STATUS, EVENTS } from "react-joyride";

interface TutorialContextType {
  startTutorial: (steps: Step[]) => void;
  isTutorialEnabled: boolean;
  toggleTutorial: () => void;
  resetTutorial: () => void;
}

const TutorialContext = createContext<TutorialContextType | undefined>(undefined);

export function useTutorial() {
  const context = useContext(TutorialContext);
  if (!context) {
    throw new Error("useTutorial must be used within TutorialProvider");
  }
  return context;
}

interface TutorialProviderProps {
  children: ReactNode;
}

export function TutorialProvider({ children }: TutorialProviderProps) {
  const [run, setRun] = useState(false);
  const [steps, setSteps] = useState<Step[]>([]);
  const [isTutorialEnabled, setIsTutorialEnabled] = useState(true);
  const [stepIndex, setStepIndex] = useState(0);
  const [mounted, setMounted] = useState(false);

  // Wait for client-side hydration before accessing localStorage
  useEffect(() => {
    setMounted(true);

    // Load tutorial preference from localStorage (client-side only)
    const enabled = localStorage.getItem("claude-nine-tutorial-enabled");
    if (enabled !== null) {
      setIsTutorialEnabled(enabled === "true");
    }

    // Check if user has completed tutorial
    const completed = localStorage.getItem("claude-nine-tutorial-completed");
    if (!completed && enabled !== "false") {
      // Auto-start tutorial on first visit
      const timer = setTimeout(() => {
        // Tutorial will auto-start when page-specific steps are set
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, []);

  const startTutorial = (newSteps: Step[]) => {
    if (!isTutorialEnabled) return;

    setSteps(newSteps);
    setStepIndex(0);
    setRun(true);
  };

  const toggleTutorial = () => {
    const newValue = !isTutorialEnabled;
    setIsTutorialEnabled(newValue);
    localStorage.setItem("claude-nine-tutorial-enabled", String(newValue));

    if (!newValue) {
      setRun(false);
    }
  };

  const resetTutorial = () => {
    localStorage.removeItem("claude-nine-tutorial-completed");
    setStepIndex(0);
  };

  const handleJoyrideCallback = (data: CallBackProps) => {
    const { status, type, index } = data;
    const finishedStatuses: string[] = [STATUS.FINISHED, STATUS.SKIPPED];

    if (finishedStatuses.includes(status)) {
      setRun(false);
      localStorage.setItem("claude-nine-tutorial-completed", "true");
    }

    if (type === EVENTS.STEP_AFTER) {
      setStepIndex(index + 1);
    }
  };

  return (
    <TutorialContext.Provider
      value={{
        startTutorial,
        isTutorialEnabled,
        toggleTutorial,
        resetTutorial,
      }}
    >
      {children}
      {mounted && (
        <Joyride
          steps={steps}
          run={run}
          stepIndex={stepIndex}
          continuous
          showProgress
          showSkipButton
          callback={handleJoyrideCallback}
          styles={{
            options: {
              primaryColor: "#2563eb",
              zIndex: 10000,
            },
            tooltip: {
              fontSize: 14,
            },
            buttonNext: {
              backgroundColor: "#2563eb",
              borderRadius: "0.375rem",
              padding: "0.5rem 1rem",
            },
            buttonBack: {
              color: "#6b7280",
              marginRight: "0.5rem",
            },
            buttonSkip: {
              color: "#6b7280",
            },
          }}
          locale={{
            back: "Back",
            close: "Close",
            last: "Finish",
            next: "Next",
            skip: "Skip Tour",
          }}
        />
      )}
    </TutorialContext.Provider>
  );
}

// Tutorial steps for different pages
export const homeTutorialSteps: Step[] = [
  {
    target: "body",
    content: (
      <div>
        <h2 className="text-xl font-bold mb-2">Welcome to Claude-Nine! 👋</h2>
        <p>
          This quick tour will show you around the platform. You can skip it anytime
          and re-enable it in settings.
        </p>
      </div>
    ),
    placement: "center",
    disableBeacon: true,
  },
  {
    target: '[data-tour="team-management"]',
    content: (
      <div>
        <h3 className="font-bold mb-1">Team Management</h3>
        <p>
          Create and manage your AI development teams. Each team can have multiple
          agents working together.
        </p>
      </div>
    ),
  },
  {
    target: '[data-tour="work-queue"]',
    content: (
      <div>
        <h3 className="font-bold mb-1">Work Queue</h3>
        <p>
          Assign work items from Azure DevOps, Jira, GitHub, or create manual tasks
          for your teams to work on.
        </p>
      </div>
    ),
  },
  {
    target: '[data-tour="monitoring"]',
    content: (
      <div>
        <h3 className="font-bold mb-1">Real-time Monitoring</h3>
        <p>
          Monitor your teams and agents in real-time. See what they're working on,
          track progress, and view metrics.
        </p>
      </div>
    ),
  },
  {
    target: '[data-tour="theme-toggle"]',
    content: (
      <div>
        <h3 className="font-bold mb-1">Theme Toggle</h3>
        <p>Switch between light and dark mode to match your preference.</p>
      </div>
    ),
  },
];

export const teamsTutorialSteps: Step[] = [
  {
    target: '[data-tour="search-teams"]',
    content: (
      <div>
        <h3 className="font-bold mb-1">Search Teams</h3>
        <p>Quickly filter teams by name or product. Results update instantly as you type.</p>
      </div>
    ),
    disableBeacon: true,
  },
  {
    target: '[data-tour="new-team-button"]',
    content: (
      <div>
        <h3 className="font-bold mb-1">Create New Team</h3>
        <p>Click here to create a new AI development team with custom agents.</p>
      </div>
    ),
  },
  {
    target: '[data-tour="team-card"]',
    content: (
      <div>
        <h3 className="font-bold mb-1">Team Card</h3>
        <p>
          Each card shows the team's status, product, and quick actions. Click "View"
          to see team details and manage agents.
        </p>
      </div>
    ),
  },
];

export const workItemsTutorialSteps: Step[] = [
  {
    target: '[data-tour="filters"]',
    content: (
      <div>
        <h3 className="font-bold mb-1">Filter Work Items</h3>
        <p>
          Filter by status, source, or team to narrow down your work items. Great for
          finding specific items before bulk assignment.
        </p>
      </div>
    ),
    disableBeacon: true,
  },
  {
    target: '[data-tour="select-all"]',
    content: (
      <div>
        <h3 className="font-bold mb-1">Select All</h3>
        <p>
          Click this checkbox to select all visible work items at once. Perfect for
          bulk operations!
        </p>
      </div>
    ),
  },
  {
    target: '[data-tour="work-item-checkbox"]',
    content: (
      <div>
        <h3 className="font-bold mb-1">Select Items</h3>
        <p>
          Check individual work items to select them. Selected items show a blue ring
          and can be bulk assigned to teams.
        </p>
      </div>
    ),
  },
  {
    target: '[data-tour="bulk-assign-button"]',
    content: (
      <div>
        <h3 className="font-bold mb-1">Bulk Assign</h3>
        <p>
          This button appears when you have items selected. Click it to assign all
          selected items to a team's queue at once!
        </p>
      </div>
    ),
  },
  {
    target: '[data-tour="new-work-item"]',
    content: (
      <div>
        <h3 className="font-bold mb-1">Create Work Item</h3>
        <p>
          Create a new work item manually, or integrate with Azure DevOps, Jira, or
          GitHub to sync automatically.
        </p>
      </div>
    ),
  },
];
