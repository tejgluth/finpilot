import { useEffect } from "react";
import ThinkingDots from "../components/common/ThinkingDots";
import { useTradingStatus } from "../hooks/useTradingStatus";
import GuardrailSettings from "../components/permissions/GuardrailSettings";
import PermissionPanel from "../components/permissions/PermissionPanel";
import CircuitBreakerAlert from "../components/trading/CircuitBreakerAlert";
import KillSwitch from "../components/trading/KillSwitch";
import LiveUnlockGate from "../components/trading/LiveUnlockGate";
import LiveTradingNotice from "../components/trading/LiveTradingNotice";
import TradeTicket from "../components/trading/TradeTicket";
import TradingStatus from "../components/trading/TradingStatus";
import { useSettingsStore } from "../stores/settingsStore";

export default function TradingPage() {
  const { permissions, tradingStatus, error: tradingError, updateLevel, refresh } = useTradingStatus();
  const { settings, loading, error: settingsError, fetchSettings } = useSettingsStore();

  useEffect(() => {
    if (!settings && !loading && !settingsError) {
      void fetchSettings();
    }
  }, [settings, loading, settingsError, fetchSettings]);

  const error = tradingError || settingsError;

  if (error) {
    return (
      <div className="rounded-[28px] bg-white/80 p-6 shadow-soft">
        <div className="font-display text-2xl text-ink">Trading controls unavailable</div>
        <p className="mt-2 text-sm text-ink/70">{error}</p>
      </div>
    );
  }

  if (!permissions || !tradingStatus || !settings) {
    return <div className="rounded-[28px] bg-white/80 p-6 shadow-soft flex items-center gap-2">Loading trading state <ThinkingDots /></div>;
  }

  return (
    <div className="space-y-6">
      <TradingStatus status={tradingStatus} />
      <TradeTicket onSubmitted={refresh} />
      <PermissionPanel current={permissions.level} onChange={(level) => void updateLevel(level)} />
      <GuardrailSettings guardrails={settings.guardrails} />
      <CircuitBreakerAlert />
      <LiveUnlockGate status={tradingStatus} onChanged={refresh} />
      <LiveTradingNotice status={tradingStatus} />
      <KillSwitch active={tradingStatus.kill_switch.active} onChanged={refresh} />
    </div>
  );
}
