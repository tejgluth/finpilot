import type { PermissionLevel } from "../../api/types";
import Panel from "../common/Panel";
import StatusBadge from "../common/StatusBadge";

const levels: Array<{ value: PermissionLevel; label: string; tone: "good" | "warn" | "danger" }> = [
  { value: "full_manual", label: "Full Manual", tone: "good" },
  { value: "semi_auto", label: "Semi-Auto", tone: "warn" },
  { value: "full_auto", label: "Full Auto", tone: "danger" },
];

export default function PermissionPanel({
  current,
  onChange,
}: {
  current: PermissionLevel;
  onChange: (level: PermissionLevel) => void;
}) {
  return (
    <Panel title="Permission level" eyebrow="Automation">
      <p className="mb-4 text-sm leading-6 text-ink/70">
        This only changes confirmation behavior inside FinPilot. It does not lock or unlock live trading for you.
      </p>
      <div className="grid gap-3 md:grid-cols-3">
        {levels.map((level) => (
          <button
            key={level.value}
            className={`rounded-[24px] border p-4 text-left ${current === level.value ? "border-ink bg-ink text-white" : "border-ink/10 bg-slate"}`}
            onClick={() => onChange(level.value)}
          >
            <div className="mb-3">
              <StatusBadge label={level.label} tone={level.tone} />
            </div>
            <p className="text-sm opacity-80">
              {level.value === "full_manual"
                ? "Every trade needs approval."
                : level.value === "semi_auto"
                  ? "Small trades may auto-confirm."
                  : "All trades can execute within guardrails."}
            </p>
          </button>
        ))}
      </div>
    </Panel>
  );
}
