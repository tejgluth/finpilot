import clsx from "clsx";
import ThinkingDots from "../components/common/ThinkingDots";
import { useEffect, useState } from "react";
import InlineTeamNameEditor from "../components/studio/InlineTeamNameEditor";
import TeamClassificationBadge from "../components/studio/TeamClassificationBadge";
import TeamStudio from "../components/studio/TeamStudio";
import AgentTeamCard from "../components/strategy/AgentTeamCard";
import PremadeTeamBrowser from "../components/strategy/PremadeTeamBrowser";
import SavedTeamsPanel from "../components/strategy/SavedTeamsPanel";
import StrategyChat from "../components/strategy/StrategyChat";
import TeamSelectorDropdown from "../components/strategy/TeamSelectorDropdown";
import TeamComparison from "../components/strategy/TeamComparison";
import TeamVisualizationView from "../components/visualization/TeamVisualizationView";
import { useCustomTeamStore } from "../stores/customTeamStore";
import { useStrategyStore } from "../stores/strategyStore";

type Tab = "build" | "visualize" | "compare" | "custom";
type CustomVisualizationMode = "custom" | "saved";

const TABS: { id: Tab; label: string }[] = [
  { id: "build", label: "Build" },
  { id: "visualize", label: "Visualize" },
  { id: "compare", label: "Compare" },
  { id: "custom", label: "Custom Team" },
];

const SEED_SUGGESTIONS = [
  "Technical-focused short-term team with momentum secondary",
  "Macro-driven conservative team, avoid growth stocks",
  "Balanced fundamentals + sentiment team for mid-cap equity",
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
  const [customSeedPrompt, setCustomSeedPrompt] = useState("");
  const [customVisualizationMode, setCustomVisualizationMode] = useState<CustomVisualizationMode>("custom");

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
    saving,
    selectTeam,
    deleteTeam,
    sendMessage,
    compileDraft,
    teams,
    updateDraftHorizon,
    updateDraftRisk,
    updateDraftWeight,
    toggleDraftAgent,
  } = useStrategyStore();

  const {
    compiledTeam: customCompiledTeam,
    conversation: customConversation,
    draft: customDraft,
    hydrate: hydrateCustom,
    loading: customLoading,
    error: customError,
    startConversation: startCustomConversation,
    compileDraft: compileCustomDraft,
    clearError: clearCustomError,
    saveTeam: saveCustomTeam,
    saving: savingCustom,
    updateTeamName: updateCustomTeamName,
  } = useCustomTeamStore();

  useEffect(() => {
    void hydrate();
    void loadPremadeCatalog();
  }, [hydrate, loadPremadeCatalog]);

  useEffect(() => {
    void hydrateCustom();
  }, [hydrateCustom]);

  useEffect(() => {
    if (!customConversation) {
      setCustomVisualizationMode("custom");
    }
  }, [customConversation]);

  async function handleCustomStart(e: React.FormEvent) {
    e.preventDefault();
    const prompt = customSeedPrompt.trim() || undefined;
    const started = await startCustomConversation(prompt);
    if (started) setCustomSeedPrompt("");
  }

  const latestTurn = customConversation?.latest_turn;
  const hasCustomTopology = Boolean(customDraft?.topology?.nodes?.length);
  const hasCustomVisualization = hasCustomTopology || Boolean(customCompiledTeam);
  const customVisualizationLabel =
    customCompiledTeam?.name ?? customDraft?.proposed_name ?? "Current custom draft";
  const customVisualizationSubtitle =
    customCompiledTeam ? "Current custom builder draft" : "In-progress custom team";
  const strategyVisualizationTeam = activeTeam?.compiled_team ?? compiledTeam;
  const modeBadges = latestTurn
    ? [
        { label: "Analyze", supported: latestTurn.mode_compatibility.analyze },
        { label: "Paper", supported: latestTurn.mode_compatibility.paper },
        { label: "Live", supported: latestTurn.mode_compatibility.live },
        { label: "Strict BT", supported: latestTurn.mode_compatibility.backtest_strict },
        { label: "Exp BT", supported: latestTurn.mode_compatibility.backtest_experimental },
      ]
    : [];

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
              onDelete={(teamId, versionNumber) => void deleteTeam(teamId, versionNumber)}
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
        {strategyVisualizationTeam ? (
          <TeamVisualizationView
            comparison={comparison}
            showComparison={false}
            team={strategyVisualizationTeam}
            teamSelector={{
              activeTeam,
              currentLabel: activeTeam?.compiled_team.name ?? strategyVisualizationTeam.name,
              currentSubtitle: activeTeam ? `v${activeTeam.version_number} · active team` : undefined,
              disabled: saving,
              onSelectTeam: (teamId, versionNumber) => selectTeam(teamId, versionNumber),
              teams,
            }}
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

      {/* Custom Team panel */}
      <div
        aria-labelledby="tab-custom"
        hidden={activeTab !== "custom"}
        id="panel-custom"
        role="tabpanel"
      >
        {!customConversation ? (
          // No conversation yet — seed prompt
          <div className="rounded-[28px] border border-white/70 bg-white/80 p-8 shadow-soft backdrop-blur-sm">
            <p className="mb-1 font-mono text-[10px] uppercase tracking-widest text-ink/40">
              Custom Team Builder
            </p>
            <h2 className="mb-2 font-display text-xl font-semibold text-ink">
              Design your own agent team
            </h2>
            <p className="mb-6 text-sm leading-relaxed text-ink/60">
              Describe the team you want to build — which analysis signals to include, your risk
              tolerance, time horizon, and any sectors to avoid.
            </p>

            {customError && (
              <div className="mb-4 flex items-start justify-between gap-3 rounded-xl bg-ember/10 px-4 py-3">
                <p className="text-sm text-ember">{customError}</p>
                <button
                  className="text-[12px] text-ember/70 hover:text-ember"
                  onClick={clearCustomError}
                  type="button"
                >
                  Dismiss
                </button>
              </div>
            )}

            <div className="mb-4 flex flex-wrap gap-2">
              {SEED_SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  className="rounded-full border border-tide/30 bg-tide/5 px-3 py-1.5 text-[12px] text-tide hover:bg-tide/10"
                  onClick={() => setCustomSeedPrompt(s)}
                  type="button"
                >
                  {s}
                </button>
              ))}
            </div>

            <form className="space-y-3" onSubmit={handleCustomStart}>
              <textarea
                className="w-full min-h-28 resize-none rounded-[20px] border border-ink/10 bg-slate/50 px-4 py-3 text-sm text-ink focus:border-tide focus:outline-none focus:ring-2 focus:ring-tide/20"
                onChange={(e) => setCustomSeedPrompt(e.target.value)}
                placeholder="Describe the team you want to build…"
                value={customSeedPrompt}
              />
              <div className="flex justify-end">
                <button
                  className="rounded-full bg-tide px-6 py-2.5 text-sm font-semibold text-white hover:bg-tide/90 disabled:opacity-40"
                  disabled={customLoading}
                  type="submit"
                >
                  {customLoading ? <ThinkingDots className="text-white" /> : "Start building"}
                </button>
              </div>
            </form>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Visualization at the top */}
            {customVisualizationMode === "saved" && activeTeam ? (
              <TeamVisualizationView
                comparison={null}
                showComparison={false}
                team={activeTeam.compiled_team}
                teamSelector={{
                  activeTeam,
                  currentLabel: activeTeam.compiled_team.name,
                  currentSubtitle: `v${activeTeam.version_number} · active team`,
                  disabled: saving,
                  extraOptions: hasCustomVisualization
                    ? [
                        {
                          key: "custom-draft",
                          label: customVisualizationLabel,
                          subtitle: customVisualizationSubtitle,
                          active: false,
                          onSelect: () => setCustomVisualizationMode("custom"),
                        },
                      ]
                    : [],
                  onSelectTeam: async (teamId, versionNumber) => {
                    await selectTeam(teamId, versionNumber);
                    setCustomVisualizationMode("saved");
                  },
                  teams,
                }}
              />
            ) : hasCustomTopology ? (
              <TeamStudio
                titleSlot={
                  <TeamSelectorDropdown
                    activeTeam={activeTeam}
                    currentLabel={customVisualizationLabel}
                    currentSubtitle={customVisualizationSubtitle}
                    disabled={saving}
                    extraOptions={
                      hasCustomVisualization
                        ? [
                            {
                              key: "custom-draft",
                              label: customVisualizationLabel,
                              subtitle: customVisualizationSubtitle,
                              active: true,
                              onSelect: () => setCustomVisualizationMode("custom"),
                            },
                          ]
                        : []
                    }
                    labelClassName="text-lg"
                    onSelectTeam={async (teamId, versionNumber) => {
                      await selectTeam(teamId, versionNumber);
                      setCustomVisualizationMode("saved");
                    }}
                    teams={teams}
                  />
                }
              />
            ) : (
              <div className="flex h-32 items-center justify-center rounded-[20px] border border-ink/8 bg-white text-[13px] text-ink/40">
                Building topology <ThinkingDots className="text-ink/40" />
              </div>
            )}

            {/* Compile action — draft exists but not yet compiled */}
            {hasCustomTopology && !customCompiledTeam && (
              <div className="flex items-center justify-between gap-4 rounded-[20px] border border-ink/8 bg-white px-5 py-4">
                <div>
                  <p className="text-sm font-medium text-ink">
                    Topology ready — {customDraft!.topology.nodes.length} nodes
                  </p>
                  <p className="text-[12px] text-ink/50">
                    {customDraft?.proposed_name ?? "Custom Team"}
                  </p>
                </div>
                <button
                  className="rounded-full bg-ink px-6 py-2.5 text-sm font-semibold text-white hover:bg-ink/80 disabled:opacity-40"
                  disabled={customLoading}
                  onClick={() => void compileCustomDraft()}
                  type="button"
                >
                  {customLoading ? <ThinkingDots className="text-white" /> : "Compile team →"}
                </button>
              </div>
            )}

            {/* Save / Start over — compiled team exists */}
            {customCompiledTeam && (
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-[20px] border border-ink/8 bg-white px-5 py-4">
                <div className="flex items-center gap-3">
                  <div>
                    <InlineTeamNameEditor
                      name={customCompiledTeam.name}
                      onSave={(name) => void updateCustomTeamName(name)}
                    />
                    <p className="text-[12px] text-ink/50">{customCompiledTeam.description}</p>
                  </div>
                  <TeamClassificationBadge
                    classification={customCompiledTeam.team_classification}
                    size="md"
                  />
                </div>
                <div className="flex gap-3">
                  <button
                    className="rounded-full border border-ink/10 px-4 py-2 text-sm text-ink/70 hover:bg-slate"
                    onClick={() => useCustomTeamStore.getState().reset()}
                    type="button"
                  >
                    Start over
                  </button>
                  <button
                    className="rounded-full bg-ink px-5 py-2 text-sm font-semibold text-white hover:bg-ink/80 disabled:opacity-40"
                    disabled={savingCustom}
                    onClick={() => void saveCustomTeam(`${customCompiledTeam.name} — Custom`)}
                    type="button"
                  >
                    {savingCustom ? <ThinkingDots className="text-white" /> : "Save team"}
                  </button>
                </div>
              </div>
            )}

            {/* Graph changes · mode support · resolved requirements */}
            {latestTurn && (
              <div className="grid gap-4 lg:grid-cols-3">
                <div className="rounded-[20px] border border-ink/8 bg-white px-5 py-4">
                  <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-ink/35">
                    Resolved
                  </p>
                  <div className="space-y-2">
                    {latestTurn.resolved_requirements.length > 0 ? (
                      latestTurn.resolved_requirements.map((item) => (
                        <div key={item.requirement_id} className="rounded-xl bg-emerald-50 px-3 py-2">
                          <p className="text-[11px] font-medium text-emerald-800">{item.label}</p>
                          <p className="text-[12px] text-emerald-700">{item.value}</p>
                        </div>
                      ))
                    ) : (
                      <p className="text-[12px] text-ink/45">
                        The architect is still gathering the core design requirements.
                      </p>
                    )}
                  </div>
                </div>

                <div className="rounded-[20px] border border-ink/8 bg-white px-5 py-4">
                  <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-ink/35">
                    Graph Changes
                  </p>
                  <div className="space-y-2">
                    {latestTurn.graph_change_summary.length > 0 ? (
                      latestTurn.graph_change_summary.map((item, index) => (
                        <p
                          key={index}
                          className="rounded-xl bg-slate/60 px-3 py-2 text-[12px] text-ink/75"
                        >
                          {item}
                        </p>
                      ))
                    ) : (
                      <p className="text-[12px] text-ink/45">No graph diff yet.</p>
                    )}
                  </div>
                </div>

                <div className="rounded-[20px] border border-ink/8 bg-white px-5 py-4">
                  <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-ink/35">
                    Mode Support
                  </p>
                  <div className="grid grid-cols-2 gap-2">
                    {modeBadges.map(({ label, supported }) => (
                      <div
                        key={label}
                        className={clsx(
                          "rounded-xl border px-2 py-1.5 text-center text-[11px] font-medium",
                          supported
                            ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                            : "border-ember/20 bg-ember/5 text-ember",
                        )}
                      >
                        {label}
                      </div>
                    ))}
                  </div>
                  {latestTurn.mode_compatibility.reasons.length > 0 && (
                    <div className="mt-3 space-y-1">
                      {latestTurn.mode_compatibility.reasons.slice(0, 4).map((reason, index) => (
                        <p key={index} className="text-[11px] text-ink/55">
                          • {reason}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Capability gaps */}
            {latestTurn && latestTurn.capability_gaps.length > 0 && (
              <div className="rounded-[20px] border border-gold/30 bg-gold/5 px-5 py-4">
                <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-gold">
                  Capability Gaps
                </p>
                <div className="space-y-2">
                  {latestTurn.capability_gaps.map((gap) => (
                    <div key={gap.capability_id} className="rounded-xl bg-white/70 px-3 py-2">
                      <p className="text-[12px] font-medium text-ink">{gap.label}</p>
                      <p className="text-[12px] text-ink/65">{gap.detail}</p>
                      {gap.recommended_action && (
                        <p className="mt-1 text-[11px] text-ink/45">{gap.recommended_action}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Error */}
            {customError && (
              <div className="flex items-start justify-between gap-3 rounded-xl bg-ember/10 px-4 py-3">
                <p className="text-sm text-ember">{customError}</p>
                <button
                  className="text-[12px] text-ember/70 hover:text-ember"
                  onClick={clearCustomError}
                  type="button"
                >
                  Dismiss
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
