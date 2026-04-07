import clsx from "clsx";
import type { TeamExecutionProfile } from "../../api/types";

interface Props {
  profile: TeamExecutionProfile | undefined;
}

interface ModeRow {
  label: string;
  key: keyof Pick<
    TeamExecutionProfile,
    | "backtest_strict_eligible"
    | "backtest_experimental_eligible"
    | "paper_eligible"
    | "live_eligible"
  >;
  description: string;
}

const MODES: ModeRow[] = [
  {
    label: "Backtest (Strict)",
    key: "backtest_strict_eligible",
    description: "Historical simulation with strict temporal integrity",
  },
  {
    label: "Backtest (Experimental)",
    key: "backtest_experimental_eligible",
    description: "Relaxed temporal rules — results may not reflect real performance",
  },
  {
    label: "Paper Trading",
    key: "paper_eligible",
    description: "Simulated real-time trading without capital at risk",
  },
  {
    label: "Live Trading",
    key: "live_eligible",
    description: "Real capital — review all warnings before enabling",
  },
];

function EligibilityRow({
  label,
  eligible,
  description,
}: {
  label: string;
  eligible: boolean;
  description: string;
}) {
  return (
    <div className="flex items-center justify-between gap-3 py-2">
      <div className="min-w-0">
        <p className="text-[12px] font-medium text-ink">{label}</p>
        <p className="text-[11px] text-ink/50">{description}</p>
      </div>
      <span
        className={clsx(
          "shrink-0 rounded-full px-2 py-0.5 font-mono text-[10px] font-semibold",
          eligible
            ? "bg-pine/10 text-pine ring-1 ring-pine/30"
            : "bg-ember/10 text-ember ring-1 ring-ember/30",
        )}
      >
        {eligible ? "Eligible" : "Blocked"}
      </span>
    </div>
  );
}

export default function BacktestEligibilityPanel({ profile }: Props) {
  if (!profile) return null;

  const reasons = profile.ineligibility_reasons ?? [];
  const warnings = profile.experimental_warnings ?? [];

  return (
    <div className="rounded-xl border border-ink/10 bg-white p-4">
      <p className="mb-3 font-mono text-[10px] uppercase tracking-widest text-ink/40">
        Execution Eligibility
      </p>
      <div className="divide-y divide-ink/6">
        {MODES.map((mode) => (
          <EligibilityRow
            key={mode.key}
            description={mode.description}
            eligible={profile[mode.key] ?? false}
            label={mode.label}
          />
        ))}
      </div>
      {reasons.length > 0 && (
        <div className="mt-3 rounded-lg bg-ember/5 px-3 py-2">
          {reasons.map((r, i) => (
            <p key={i} className="text-[11px] text-ember/80">
              • {r}
            </p>
          ))}
        </div>
      )}
      {warnings.length > 0 && (
        <div className="mt-2 rounded-lg bg-gold/5 px-3 py-2">
          {warnings.map((w, i) => (
            <p key={i} className="text-[11px] text-gold/80">
              ⚠ {w}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
