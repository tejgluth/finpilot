import { useEffect, useState } from "react";
import type { PremadeTeamCatalog, PremadeTeamTemplate } from "../../api/types";
import Panel from "../common/Panel";

const RISK_COLORS: Record<string, string> = {
  conservative: "bg-emerald-100 text-emerald-800",
  moderate: "bg-sky-100 text-sky-800",
  aggressive: "bg-rose-100 text-rose-800",
};

const COMPLEXITY_LABEL: Record<string, string> = {
  beginner: "Beginner-friendly",
  intermediate: "Intermediate",
  advanced: "Advanced",
};

function TeamCard({
  template,
  onApply,
  applying,
}: {
  template: PremadeTeamTemplate;
  onApply: (teamId: string) => void;
  applying: boolean;
}) {
  return (
    <div className="flex flex-col gap-3 rounded-[24px] border border-ink/10 bg-white p-5">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-ink">{template.display_name}</span>
            {template.is_default && (
              <span className="rounded-full bg-tide/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest text-tide">
                Default
              </span>
            )}
          </div>
          <div className="mt-0.5 text-[11px] text-ink/50">{COMPLEXITY_LABEL[template.complexity]}</div>
        </div>
        <div className="flex flex-shrink-0 flex-col items-end gap-1">
          <span
            className={`rounded-full px-2 py-0.5 text-[10px] font-semibold capitalize ${RISK_COLORS[template.risk_level] ?? "bg-slate-100 text-slate-700"}`}
          >
            {template.risk_level}
          </span>
          <span className="text-[10px] text-ink/50 capitalize">{template.time_horizon} horizon</span>
        </div>
      </div>

      <p className="text-xs leading-relaxed text-ink/70">{template.description}</p>

      <div className="flex flex-wrap gap-1.5">
        {template.enabled_analysis_agents.map((agent) => (
          <span
            className="rounded-full border border-ink/10 bg-slate/60 px-2.5 py-0.5 text-[10px] font-medium capitalize text-ink/70"
            key={agent}
          >
            {agent}
          </span>
        ))}
      </div>

      {template.excluded_sectors.length > 0 && (
        <div className="text-[11px] text-ink/50">
          Excludes: {template.excluded_sectors.map((s) => s.replace(/_/g, " ")).join(", ")}
        </div>
      )}

      <button
        className="mt-1 w-full rounded-full border border-tide px-4 py-2 text-xs font-semibold text-tide transition hover:bg-tide hover:text-white disabled:opacity-40"
        disabled={applying}
        onClick={() => onApply(template.team_id)}
        type="button"
      >
        {applying ? "Applying…" : "Use this team"}
      </button>
    </div>
  );
}

export default function PremadeTeamBrowser({
  catalog,
  onApply,
  applying,
}: {
  catalog: PremadeTeamCatalog;
  onApply: (teamId: string) => void;
  applying: boolean;
}) {
  const [showAll, setShowAll] = useState(false);

  const featured = catalog.featured_team_ids
    .map((id) => catalog.teams.find((t) => t.team_id === id))
    .filter(Boolean) as PremadeTeamTemplate[];

  const regular = catalog.teams.filter(
    (t) => !t.is_hidden && !catalog.featured_team_ids.includes(t.team_id),
  );

  const hidden = catalog.hidden_team_ids
    .map((id) => catalog.teams.find((t) => t.team_id === id))
    .filter(Boolean) as PremadeTeamTemplate[];

  const visible = showAll ? [...featured, ...regular, ...hidden] : [...featured, ...regular];

  return (
    <Panel title="Premade teams" eyebrow="Strategy">
      <div className="space-y-4">
        <p className="text-sm text-ink/60">
          Select a premade starting point. You can adjust weights and settings after applying.
        </p>

        <div className="grid gap-4 md:grid-cols-2">
          {visible.map((template) => (
            <TeamCard
              applying={applying}
              key={template.team_id}
              onApply={onApply}
              template={template}
            />
          ))}
        </div>

        {!showAll && hidden.length > 0 && (
          <button
            className="w-full rounded-full border border-ink/15 py-2.5 text-xs font-semibold text-ink/60 transition hover:border-ink/30 hover:text-ink/80"
            onClick={() => setShowAll(true)}
            type="button"
          >
            Show {hidden.length} more teams
          </button>
        )}

        {showAll && (
          <button
            className="w-full rounded-full border border-ink/15 py-2.5 text-xs font-semibold text-ink/60 transition hover:border-ink/30 hover:text-ink/80"
            onClick={() => setShowAll(false)}
            type="button"
          >
            Show fewer
          </button>
        )}
      </div>
    </Panel>
  );
}
