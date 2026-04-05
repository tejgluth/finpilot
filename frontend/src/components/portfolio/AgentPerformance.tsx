import Panel from "../common/Panel";

export default function AgentPerformance({
  items,
}: {
  items: { agent_name: string; accuracy_pct: number }[];
}) {
  if (!items.length) {
    return (
      <Panel title="Per-agent local accuracy" eyebrow="Attribution">
        <div className="rounded-2xl bg-slate px-4 py-5 text-sm text-ink/65">
          Agent-level attribution is hidden until FinPilot can calculate it honestly from stored decisions and outcomes.
        </div>
      </Panel>
    );
  }

  return (
    <Panel title="Per-agent local accuracy" eyebrow="Attribution">
      <div className="space-y-3">
        {items.map((item) => (
          <div key={item.agent_name} className="rounded-2xl bg-slate px-4 py-3">
            <div className="flex items-center justify-between">
              <span className="font-semibold capitalize">{item.agent_name}</span>
              <span className="font-mono text-xs">{item.accuracy_pct}%</span>
            </div>
            <div className="mt-2 h-2 rounded-full bg-white">
              <div className="h-2 rounded-full bg-tide" style={{ width: `${item.accuracy_pct}%` }} />
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}
