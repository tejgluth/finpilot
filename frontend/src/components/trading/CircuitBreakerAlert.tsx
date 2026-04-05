import Panel from "../common/Panel";

export default function CircuitBreakerAlert() {
  return (
    <Panel title="Circuit breakers" eyebrow="Safety">
      <p className="text-sm text-ink/70">
        Daily loss, weekly drawdown, total drawdown, and max-trades-per-day checks run server-side before execution.
      </p>
    </Panel>
  );
}
