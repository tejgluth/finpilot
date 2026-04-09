import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import clsx from "clsx";
import ThinkingDots from "../components/common/ThinkingDots";
import { useSettings } from "../hooks/useSettings";
import AgentSettingsPanel from "../components/settings/AgentSettings";
import BacktestSettingsPanel from "../components/settings/BacktestSettings";
import DataSourceSettingsPanel from "../components/settings/DataSourceSettings";
import GuardrailSettingsPanel from "../components/settings/GuardrailSettingsPanel";
import LlmSettingsPanel from "../components/settings/LlmSettings";
import SystemSettingsPanel from "../components/settings/SystemSettings";

const SETTINGS_TABS = ["llm", "data", "agents", "backtest", "guardrails", "system"] as const;
type SettingsTab = (typeof SETTINGS_TABS)[number];

const TAB_LABELS: Record<SettingsTab, string> = {
  llm: "LLM",
  data: "Data",
  agents: "Agents",
  backtest: "Backtest",
  guardrails: "Guardrails",
  system: "System",
};

function isSettingsTab(value: string | null): value is SettingsTab {
  return value !== null && SETTINGS_TABS.includes(value as SettingsTab);
}

export default function SettingsPage() {
  const { settings, loading, error, patchSettings } = useSettings();
  const [searchParams, setSearchParams] = useSearchParams();
  const searchTab = searchParams.get("tab");
  const [tab, setTab] = useState<SettingsTab>(isSettingsTab(searchTab) ? searchTab : "llm");
  const focusKey = searchParams.get("focus");

  useEffect(() => {
    if (isSettingsTab(searchTab)) {
      setTab(searchTab);
    }
  }, [searchTab]);

  function handleTabChange(nextTab: SettingsTab) {
    setTab(nextTab);
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set("tab", nextTab);
    if (nextTab !== "data") {
      nextParams.delete("focus");
    }
    setSearchParams(nextParams, { replace: true });
  }

  if (error && !settings) {
    return (
      <div className="rounded-[28px] bg-white/80 p-6 shadow-soft text-sm text-ink/70">
        Unable to load settings: {error}
      </div>
    );
  }

  if (!settings) {
    return (
      <div className="rounded-[28px] bg-white/80 p-6 shadow-soft flex items-center gap-2 text-sm text-ink/70">
        Loading settings <ThinkingDots />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Tab bar */}
      <div
        aria-label="Settings sections"
        className="flex gap-1 rounded-full bg-slate p-1 w-fit"
        role="tablist"
      >
        {SETTINGS_TABS.map((value) => (
          <button
            aria-controls={`settings-panel-${value}`}
            aria-selected={tab === value}
            className={clsx(
              "rounded-full px-4 py-2 text-sm font-medium transition-all",
              tab === value
                ? "bg-white text-ink shadow-sm"
                : "text-ink/50 hover:text-ink/80",
            )}
            id={`settings-tab-${value}`}
            key={value}
            onClick={() => handleTabChange(value)}
            role="tab"
            type="button"
          >
            {TAB_LABELS[value]}
          </button>
        ))}
      </div>

      {tab === "llm" && (
        <div id="settings-panel-llm" role="tabpanel" aria-labelledby="settings-tab-llm">
          <LlmSettingsPanel onSave={patchSettings} saving={loading} settings={settings.llm} />
        </div>
      )}
      {tab === "data" && (
        <div id="settings-panel-data" role="tabpanel" aria-labelledby="settings-tab-data">
          <DataSourceSettingsPanel
            highlightKey={focusKey}
            onSave={patchSettings}
            saving={loading}
            settings={settings.data_sources}
          />
        </div>
      )}
      {tab === "agents" && (
        <div id="settings-panel-agents" role="tabpanel" aria-labelledby="settings-tab-agents">
          <AgentSettingsPanel onSave={patchSettings} saving={loading} settings={settings.agents} />
        </div>
      )}
      {tab === "backtest" && (
        <div id="settings-panel-backtest" role="tabpanel" aria-labelledby="settings-tab-backtest">
          <BacktestSettingsPanel onSave={patchSettings} saving={loading} settings={settings.backtest} />
        </div>
      )}
      {tab === "guardrails" && (
        <div id="settings-panel-guardrails" role="tabpanel" aria-labelledby="settings-tab-guardrails">
          <GuardrailSettingsPanel onSave={patchSettings} saving={loading} settings={settings.guardrails} />
        </div>
      )}
      {tab === "system" && (
        <div id="settings-panel-system" role="tabpanel" aria-labelledby="settings-tab-system">
          <SystemSettingsPanel onSave={patchSettings} saving={loading} settings={settings.system} />
        </div>
      )}
    </div>
  );
}
