import type { DecisionEvent } from "../../api/types";
import Panel from "../common/Panel";

export default function BullBearDebate({ decisionEvents }: { decisionEvents: DecisionEvent[] }) {
  const debateEvents = decisionEvents
    .filter((event) => event.bull_case || event.bear_case)
    .slice(0, 4);

  return (
    <Panel title="Bull / bear debate" eyebrow="Cross-check">
      {debateEvents.length ? (
        <div className="space-y-4">
          {debateEvents.map((event) => (
            <div key={`${event.team_id}:${event.version_number}:${event.rebalance_date}:${event.ticker}`} className="rounded-[24px] bg-slate p-4">
              <div className="mb-4 font-display text-lg">
                {event.team_name} v{event.version_number} · {event.ticker}
              </div>
              <div className="grid gap-4 lg:grid-cols-2">
                <div className="rounded-[24px] bg-pine/8 p-4">
                  <div className="font-display text-lg">Bull case</div>
                  <p className="mt-2 text-sm text-ink/70">{event.bull_case?.thesis ?? "No bull case generated."}</p>
                  <ul className="mt-3 space-y-2 text-sm text-ink/70">
                    {(event.bull_case?.key_points ?? []).map((point) => (
                      <li key={point}>{point}</li>
                    ))}
                  </ul>
                </div>
                <div className="rounded-[24px] bg-ember/8 p-4">
                  <div className="font-display text-lg">Bear case</div>
                  <p className="mt-2 text-sm text-ink/70">{event.bear_case?.thesis ?? "No bear case generated."}</p>
                  <ul className="mt-3 space-y-2 text-sm text-ink/70">
                    {(event.bear_case?.key_points ?? []).map((point) => (
                      <li key={point}>{point}</li>
                    ))}
                  </ul>
                </div>
              </div>
              <div className="mt-4 rounded-[24px] bg-white/80 p-4 text-sm text-ink/70">
                {event.decision.reasoning}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded-[24px] bg-slate p-4 text-sm text-ink/65">
          No bull/bear debate traces were captured for this run.
        </div>
      )}
    </Panel>
  );
}
