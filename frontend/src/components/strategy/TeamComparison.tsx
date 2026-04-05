import type { TeamComparison } from "../../api/types";
import Panel from "../common/Panel";

export default function TeamComparisonPanel({ comparison }: { comparison: TeamComparison | null }) {
  if (!comparison) {
    return (
      <Panel title="Default comparison" eyebrow="Comparison">
        <p className="text-sm text-ink/60">Compile a draft to see how it differs from the premade default team.</p>
      </Panel>
    );
  }

  return (
    <Panel title="Default comparison" eyebrow="Comparison">
      <div className="space-y-3 text-sm text-ink/75">
        <p>{comparison.summary}</p>
        {comparison.agent_diff.added.length ? <p>Added: {comparison.agent_diff.added.join(", ")}</p> : null}
        {comparison.agent_diff.removed.length ? <p>Removed: {comparison.agent_diff.removed.join(", ")}</p> : null}
        <div className="rounded-2xl bg-slate px-4 py-3">
          <div className="mb-2 text-xs font-mono uppercase tracking-[0.3em] text-ink/50">Weight deltas</div>
          <div className="space-y-1">
            {Object.entries(comparison.weight_diff).length ? (
              Object.entries(comparison.weight_diff).map(([agent, value]) => (
                <div className="flex justify-between" key={agent}>
                  <span className="capitalize">{agent}</span>
                  <span>
                    {value.default}% → {value.candidate}%
                  </span>
                </div>
              ))
            ) : (
              <div>No weight changes versus default.</div>
            )}
          </div>
        </div>
      </div>
    </Panel>
  );
}
