import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import ThinkingDots from "../components/common/ThinkingDots";
import { useSettings } from "../hooks/useSettings";
import AgentSettingsPanel from "../components/settings/AgentSettings";
import BacktestSettingsPanel from "../components/settings/BacktestSettings";
import DataSourceSettingsPanel from "../components/settings/DataSourceSettings";
import GuardrailSettingsPanel from "../components/settings/GuardrailSettingsPanel";
import LlmSettingsPanel from "../components/settings/LlmSettings";
import SystemSettingsPanel from "../components/settings/SystemSettings";
import StatusBadge from "../components/common/StatusBadge";

const SETTINGS_TABS = ["llm", "data", "agents", "backtest", "guardrails", "system"] as const;
type SettingsTab = (typeof SETTINGS_TABS)[number];

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
    return <div className="rounded-[28px] bg-white/80 p-6 shadow-soft">Unable to load settings: {error}</div>;
  }

  if (!settings) {
    return <div className="rounded-[28px] bg-white/80 p-6 shadow-soft flex items-center gap-2">Loading settings <ThinkingDots /></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-2">
        {[
          ["llm", "LLM"],
          ["data", "Data"],
          ["agents", "Agents"],
          ["backtest", "Backtest"],
          ["guardrails", "Guardrails"],
          ["system", "System"],
        ].map(([value, label]) => (
          <button
            key={value}
            className="rounded-full border border-ink/10 px-4 py-2 text-sm"
            onClick={() => handleTabChange(value as SettingsTab)}
            type="button"
          >
            <StatusBadge label={label} tone={tab === value ? "good" : "neutral"} />
          </button>
        ))}
      </div>
      {tab === "llm" ? <LlmSettingsPanel onSave={patchSettings} saving={loading} settings={settings.llm} /> : null}
      {tab === "data" ? (
        <DataSourceSettingsPanel
          highlightKey={focusKey}
          onSave={patchSettings}
          saving={loading}
          settings={settings.data_sources}
        />
      ) : null}
      {tab === "agents" ? <AgentSettingsPanel onSave={patchSettings} saving={loading} settings={settings.agents} /> : null}
      {tab === "backtest" ? <BacktestSettingsPanel onSave={patchSettings} saving={loading} settings={settings.backtest} /> : null}
      {tab === "guardrails" ? <GuardrailSettingsPanel onSave={patchSettings} saving={loading} settings={settings.guardrails} /> : null}
      {tab === "system" ? <SystemSettingsPanel onSave={patchSettings} saving={loading} settings={settings.system} /> : null}
    </div>
  );
}
