import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useSetupStore } from "../../stores/setupStore";
import ApiKeyStep from "./ApiKeyStep";
import DataSourceStep from "./DataSourceStep";
import PlanDetector from "./PlanDetector";
import ThinkingDots from "../common/ThinkingDots";

export default function SetupWizard({ focusService }: { focusService?: string | null }) {
  const navigate = useNavigate();
  const { status, plan, keys, guides, loading, saving, error, refresh, saveSecrets } = useSetupStore();

  useEffect(() => {
    void refresh();
  }, [refresh]);

  if (!status || !guides) {
    return <div className="rounded-[28px] bg-white/80 p-6 shadow-soft flex items-center gap-2">Loading setup state <ThinkingDots /></div>;
  }

  return (
    <div className="grid gap-6">
      <ApiKeyStep
        error={error}
        focusService={focusService}
        guides={guides}
        keys={keys}
        loading={loading}
        saving={saving}
        status={status}
        onSave={saveSecrets}
      />
      <DataSourceStep dataSources={status.user_settings.data_sources} />
      <PlanDetector plan={plan} />
      <div className="rounded-[28px] border border-white/70 bg-white/80 p-5 shadow-soft backdrop-blur-sm">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="font-mono text-[11px] uppercase tracking-[0.3em] text-tide/70">
              Next step
            </div>
            <h3 className="font-display text-xl text-ink">Move into Strategy when you&apos;re ready</h3>
            <p className="mt-1 text-sm leading-6 text-ink/70">
              Paper-first defaults and live-trading guardrails still apply later in the app, so setup can stay focused on your local configuration.
            </p>
          </div>
          <button
            className="rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white hover:bg-ink/90 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={!status.has_ai_provider}
            onClick={() => navigate("/strategy")}
            type="button"
          >
            Open Strategy
          </button>
        </div>
        {!status.has_ai_provider ? (
          <p className="mt-3 text-sm text-ink/60">
            Save one AI provider first, then Strategy opens with the rest of the safe defaults intact.
          </p>
        ) : null}
      </div>
    </div>
  );
}
