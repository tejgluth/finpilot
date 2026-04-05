import type { AlpacaPlanResponse } from "../../api/types";
import Panel from "../common/Panel";
import StatusBadge from "../common/StatusBadge";

export default function PlanDetector({ plan }: { plan: AlpacaPlanResponse | null }) {
  if (!plan) {
    return null;
  }
  return (
    <Panel title="Detected Alpaca plan" eyebrow="Step 3" action={<StatusBadge label={plan.display_name} tone="neutral" />}>
      <p className="text-sm text-ink/70">{plan.description}</p>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div className="rounded-2xl bg-slate px-4 py-3">
          <div className="font-mono text-xs uppercase text-ink/50">Data req/min</div>
          <div className="text-2xl font-display">{plan.data_requests_per_minute}</div>
        </div>
        <div className="rounded-2xl bg-slate px-4 py-3">
          <div className="font-mono text-xs uppercase text-ink/50">Orders/min</div>
          <div className="text-2xl font-display">{plan.orders_per_minute}</div>
        </div>
        <div className="rounded-2xl bg-slate px-4 py-3">
          <div className="font-mono text-xs uppercase text-ink/50">Orders/day</div>
          <div className="text-2xl font-display">{plan.orders_per_day}</div>
        </div>
      </div>
    </Panel>
  );
}
