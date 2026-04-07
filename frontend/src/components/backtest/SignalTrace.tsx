import type { DecisionEvent } from "../../api/types";
import ConfidenceBadge from "../common/ConfidenceBadge";
import DataFreshnessTag from "../common/DataFreshnessTag";
import HallucinationGuard from "../common/HallucinationGuard";
import Panel from "../common/Panel";

export default function SignalTrace({ decisionEvents }: { decisionEvents: DecisionEvent[] }) {
  const tracedEvents = decisionEvents
    .filter((event) => event.signals.length)
    .slice(0, 6);

  if (!tracedEvents.length) {
    return (
      <Panel title="Signal trace" eyebrow="Per-agent grounding">
        <div className="rounded-[24px] bg-slate p-4 text-sm text-ink/65">
          No per-agent signal trace was stored for this run.
        </div>
      </Panel>
    );
  }

  return (
    <Panel title="Signal trace" eyebrow="Per-agent grounding">
      <div className="space-y-4">
        {tracedEvents.map((event) => (
          <div key={`${event.team_id}:${event.version_number}:${event.rebalance_date}:${event.ticker}`} className="rounded-[24px] bg-slate p-4">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h4 className="font-display text-lg">
                  {event.team_name} v{event.version_number} · {event.ticker}
                </h4>
                <p className="text-xs text-ink/55">
                  Rebalance {event.rebalance_date} · Execute {event.execution_date} · {event.decision.action} · {event.current_weight_pct.toFixed(2)}% → {event.target_weight_pct.toFixed(2)}%
                </p>
              </div>
              <ConfidenceBadge value={event.decision.confidence} />
            </div>
            <div className="mb-4 rounded-2xl bg-white/70 px-4 py-3 text-sm text-ink/70">
              {event.selection_reason || event.exclusion_reason || "No construction note was stored for this ticker."}
            </div>
            <div className="space-y-4">
              {event.signals.map((signal) => (
                <div key={`${event.ticker}-${signal.agent_name}`} className="rounded-2xl bg-white/80 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <h5 className="font-display text-base capitalize">{signal.agent_name}</h5>
                    <ConfidenceBadge value={signal.final_confidence} />
                    <DataFreshnessTag minutes={signal.oldest_data_age_minutes} />
                    <HallucinationGuard coverage={signal.data_coverage_pct} oldestAge={signal.oldest_data_age_minutes} />
                  </div>
                  <p className="mt-3 text-sm text-ink/70">{signal.reasoning}</p>
                  {signal.cited_data.length ? (
                    <div className="mt-3 grid gap-2">
                      {signal.cited_data.map((citation) => (
                        <div key={`${signal.agent_name}-${citation.field_name}`} className="rounded-2xl bg-white px-3 py-2 text-xs text-ink/70">
                          <span className="font-semibold">{citation.field_name}</span>: {citation.value} from {citation.source}
                        </div>
                      ))}
                    </div>
                  ) : null}
                  {signal.unavailable_fields.length ? (
                    <p className="mt-2 text-xs text-ember">Unavailable: {signal.unavailable_fields.join(", ")}</p>
                  ) : null}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}
