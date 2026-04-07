import clsx from "clsx";
import type { TeamValidationResult } from "../../api/types";

interface Props {
  validationResult: TeamValidationResult | null;
}

export default function ValidationBanner({ validationResult }: Props) {
  if (!validationResult) return null;

  const errors = validationResult.errors ?? [];
  const warnings = validationResult.warnings ?? [];

  if (errors.length === 0 && warnings.length === 0) return null;

  return (
    <div className="space-y-2">
      {errors.length > 0 && (
        <div className="rounded-xl border border-ember/30 bg-ember/5 px-4 py-3">
          <p className="mb-1.5 font-mono text-[11px] font-semibold uppercase tracking-wide text-ember">
            Validation Errors
          </p>
          <ul className="space-y-1">
            {errors.map((err, i) => (
              <li
                key={i}
                className="flex items-start gap-2 text-[12px] text-ember/90"
              >
                <span className="mt-0.5 shrink-0">•</span>
                <span>{err}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {warnings.length > 0 && (
        <div className="rounded-xl border border-gold/30 bg-gold/5 px-4 py-3">
          <p className="mb-1.5 font-mono text-[11px] font-semibold uppercase tracking-wide text-gold">
            Warnings
          </p>
          <ul className="space-y-1">
            {warnings.map((w, i) => (
              <li
                key={i}
                className={clsx(
                  "flex items-start gap-2 text-[12px] text-gold/90",
                )}
              >
                <span className="mt-0.5 shrink-0">⚠</span>
                <span>{w}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
