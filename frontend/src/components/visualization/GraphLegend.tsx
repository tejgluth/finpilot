/**
 * Floating legend panel inside the ReactFlow graph container.
 * All meaning is conveyed with text + shape, not color alone.
 */
export default function GraphLegend() {
  return (
    <div
      aria-label="Graph legend"
      className="absolute bottom-4 left-4 z-10 rounded-2xl border border-white/70 bg-white/90 p-3 shadow-soft backdrop-blur-sm"
      role="complementary"
    >
      <p className="mb-2 font-mono text-[9px] uppercase tracking-widest text-ink/40">
        Legend
      </p>
      <div className="space-y-1.5">
        <LegendRow
          description="Reads market signals"
          indicator={<ColorBar color="bg-tide" />}
          label="Analysis agent"
        />
        <LegendRow
          description="Enforces rules & decides"
          indicator={<ColorBar color="bg-pine" />}
          label="Decision agent"
        />
        <LegendRow
          description="Agent is off in this team"
          indicator={<DashedBox />}
          label="Disabled"
        />
        <LegendRow
          description="Heavier line = more influence"
          indicator={<ThickLine />}
          label="Edge thickness"
        />
        <LegendRow
          description="Present in candidate, absent in default"
          indicator={<Badge cls="bg-emerald-100 text-emerald-800 ring-emerald-300">+ Added</Badge>}
          label=""
        />
        <LegendRow
          description="Absent in candidate"
          indicator={<Badge cls="bg-ember/10 text-ember ring-ember/30">− Removed</Badge>}
          label=""
        />
        <LegendRow
          description="Weight changed vs default"
          indicator={<Badge cls="bg-gold/10 text-gold ring-gold/30">↑↓ Weight</Badge>}
          label=""
        />
      </div>
    </div>
  );
}

function LegendRow({
  indicator,
  label,
  description,
}: {
  indicator: React.ReactNode;
  label: string;
  description: string;
}) {
  return (
    <div className="flex items-center gap-2" title={description}>
      <div className="flex w-14 shrink-0 items-center justify-center">{indicator}</div>
      <span className="text-[10px] text-ink/70">
        {label ? <strong>{label}</strong> : null}
        {label && description ? ": " : null}
        {!label ? description : null}
      </span>
    </div>
  );
}

function ColorBar({ color }: { color: string }) {
  return <div className={`h-3.5 w-1 rounded-full ${color}`} />;
}

function DashedBox() {
  return (
    <div
      className="h-3.5 w-5 rounded border border-dashed border-ink/30 opacity-50"
    />
  );
}

function ThickLine() {
  return <div className="h-0.5 w-10 rounded bg-ink/25" style={{ height: 3 }} />;
}

function Badge({
  children,
  cls,
}: {
  children: React.ReactNode;
  cls: string;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-1.5 py-0.5 font-mono text-[9px] font-semibold ring-1 ${cls}`}
    >
      {children}
    </span>
  );
}
