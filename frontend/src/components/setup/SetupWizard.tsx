import { useEffect } from "react";
import ThinkingDots from "../common/ThinkingDots";
import { useNavigate } from "react-router-dom";
import { useSetupStore } from "../../stores/setupStore";
import ApiKeyStep from "./ApiKeyStep";
import DataSourceStep from "./DataSourceStep";
import PlanDetector from "./PlanDetector";
import RiskAcknowledgment from "./RiskAcknowledgment";

export default function SetupWizard() {
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
        guides={guides}
        keys={keys}
        loading={loading}
        saving={saving}
        status={status}
        onSave={saveSecrets}
      />
      <DataSourceStep dataSources={status.user_settings.data_sources} />
      <PlanDetector plan={plan} />
      <RiskAcknowledgment canContinue={status.has_ai_provider} onComplete={() => navigate("/strategy")} />
    </div>
  );
}
