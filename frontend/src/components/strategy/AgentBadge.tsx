export default function AgentBadge({
  name,
  sources,
  variant,
  enabled,
}: {
  name: string;
  sources: string[];
  variant?: string;
  enabled?: boolean;
}) {
  return (
    <div className={`rounded-full px-3 py-1 text-sm ${enabled === false ? "bg-slate/60 text-ink/45" : "bg-slate text-ink"}`}>
      <span className="font-semibold">{name}</span>
      {variant ? <span className="ml-2 text-ink/55">{variant}</span> : null}
      {sources.length ? <span className="ml-2 text-ink/40">{sources.join(", ")}</span> : null}
    </div>
  );
}
