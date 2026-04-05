import clsx from "clsx";
import { useEffect, useState } from "react";
import AgentTeamCard from "../components/strategy/AgentTeamCard";
import PremadeTeamBrowser from "../components/strategy/PremadeTeamBrowser";
import SavedTeamsPanel from "../components/strategy/SavedTeamsPanel";
import StrategyChat from "../components/strategy/StrategyChat";
import TeamComparison from "../components/strategy/TeamComparison";
import TeamVisualizationView from "../components/visualization/TeamVisualizationView";
import { useStrategyStore } from "../stores/strategyStore";

type Tab = "build" | "visualize" | "compare";

const TABS: { id: Tab; label: string }[] = [
  { id: "build", label: "Build" },
  { id: "visualize", label: "Visualize" },
  { id: "compare", label: "Compare" },
];

function EmptyState({
  message,
  onAction,
  actionLabel,
}: {
  message: string;
  onAction: () => void;
  actionLabel: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 rounded-[28px] border border-white/70 bg-white/80 p-12 shadow-soft backdrop-blur-sm text-center">
      <p className="text-sm text-ink/60">{message}</p>
      <button
        className="rounded-full bg-ink px-5 py-2.5 text-sm font-semibold text-white hover:bg-ink/80"
        onClick={onAction}
        type="button"
      >
        {actionLabel}
      </button>
    </div>
  );
}

export default function StrategyPage() {
  const [activeTab, setActiveTab] = useState<Tab>("build");

  const {
    activeTeam,
    applyPremadeTeam,
    comparison,
    compiledTeam,
    conversation,
    error,
    hydrate,
    loading,
    loadPremadeCatalog,
    premadeCatalog,
    saveDraft,
    selectTeam,
    sendMessage,
    compileDraft,
    teams,
    updateDraftHorizon,
    updateDraftRisk,
    updateDraftWeight,
    toggleDraftAgent,
  } = useStrategyStore();

  useEffect(() => {
    void hydrate();
    void loadPremadeCatalog();
  }, [hydrate, loadPremadeCatalog]);

  return (
    <div className="space-y-4">
      {/* Tab bar */}
      <div
        aria-label="Strategy views"
        className="flex gap-1 rounded-full bg-slate p-1 w-fit"
        role="tablist"
      >
        {TABS.map(({ id, label }) => (
          <button
            aria-controls={`panel-${id}`}
            aria-selected={activeTab === id}
            className={clsx(
              "rounded-full px-5 py-2 text-sm font-semibold transition-all",
              activeTab === id
                ? "bg-white text-ink shadow-soft"
                : "text-ink/50 hover:text-ink/80",
            )}
            id={`tab-${id}`}
            key={id}
            onClick={() => setActiveTab(id)}
            role="tab"
            type="button"
          >
            {label}
          </button>
        ))}
      </div>

      {/* Build panel */}
      <div
        aria-labelledby="tab-build"
        hidden={activeTab !== "build"}
        id="panel-build"
        role="tabpanel"
      >
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)]">
          <div className="space-y-6">
            <StrategyChat
              conversation={conversation}
              error={error}
              loading={loading}
              onCompile={() => void compileDraft()}
              onSubmit={(prompt) => void sendMessage(prompt, true)}
            />
            {compiledTeam ? (
              <div className="space-y-4">
                <AgentTeamCard
                  onHorizonChange={(value) => void updateDraftHorizon(value)}
                  onRiskChange={(value) => void updateDraftRisk(value)}
                  onToggleAgent={(agent, enabled) => void toggleDraftAgent(agent, enabled)}
                  onWeightChange={(agent, value) => void updateDraftWeight(agent, value)}
                  team={compiledTeam}
                />
                <div className="flex justify-end">
                  <button
                    className="rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white"
                    onClick={() => void saveDraft(`${compiledTeam.name} Version`)}
                    type="button"
                  >
                    Save immutable version
                  </button>
                </div>
              </div>
            ) : null}
          </div>
          <div className="space-y-6">
            <TeamComparison comparison={comparison} />
            {premadeCatalog ? (
              <PremadeTeamBrowser
                applying={loading}
                catalog={premadeCatalog}
                onApply={(teamId) => void applyPremadeTeam(teamId)}
              />
            ) : null}
            <SavedTeamsPanel
              activeTeam={activeTeam}
              onSelect={(teamId, versionNumber) => void selectTeam(teamId, versionNumber)}
              teams={teams}
            />
          </div>
        </div>
      </div>

      {/* Visualize panel */}
      <div
        aria-labelledby="tab-visualize"
        hidden={activeTab !== "visualize"}
        id="panel-visualize"
        role="tabpanel"
      >
        {compiledTeam ? (
          <TeamVisualizationView
            comparison={comparison}
            showComparison={false}
            team={compiledTeam}
          />
        ) : (
          <EmptyState
            actionLabel="Go to Build"
            message="Build or select a team first to see the topology."
            onAction={() => setActiveTab("build")}
          />
        )}
      </div>

      {/* Compare panel */}
      <div
        aria-labelledby="tab-compare"
        hidden={activeTab !== "compare"}
        id="panel-compare"
        role="tabpanel"
      >
        {compiledTeam ? (
          <TeamVisualizationView
            comparison={comparison}
            showComparison={true}
            team={compiledTeam}
          />
        ) : (
          <EmptyState
            actionLabel="Go to Build"
            message="Compile a draft team to compare against the default baseline."
            onAction={() => setActiveTab("build")}
          />
        )}
      </div>
    </div>
  );
}
