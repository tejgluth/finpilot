import Panel from "../common/Panel";

const CHECKS = [
  "Daily loss limit",
  "Weekly drawdown",
  "Total drawdown",
  "Max trades per day",
];

export default function CircuitBreakerAlert() {
  return (
    <Panel title="Circuit breakers" eyebrow="Safety">
      <p className="mb-4 text-sm text-ink/70">
        These checks run server-side before any order is submitted. If a limit is breached, execution halts automatically.
      </p>
      <div className="flex flex-wrap gap-2">
        {CHECKS.map((check) => (
          <div key={check} className="flex items-center gap-1.5 rounded-full bg-pine/10 px-3 py-1.5 text-xs font-medium text-pine">
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
              <path d="M2 5.5L4 7.5L8 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            {check}
          </div>
        ))}
      </div>
    </Panel>
  );
}
