import StatusBadge from "../common/StatusBadge";

export default function TopBar() {
  return (
    <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
      <div>
        <div className="font-mono text-[11px] uppercase tracking-[0.35em] text-tide/70">Workspace</div>
        <h1 className="font-display text-4xl text-ink">Truth-first controls, local-only analytics</h1>
      </div>
      <div className="flex flex-col items-start gap-3 lg:items-end">
        <StatusBadge label="Paper default" tone="good" />
      </div>
    </header>
  );
}
