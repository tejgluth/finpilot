import clsx from "clsx";

interface StatusBadgeProps {
  label: string;
  tone?: "neutral" | "good" | "warn" | "danger";
}

export default function StatusBadge({ label, tone = "neutral" }: StatusBadgeProps) {
  return (
    <span
      className={clsx(
        "inline-flex rounded-full px-3 py-1 font-mono text-xs uppercase tracking-wide",
        tone === "good" && "bg-pine/10 text-pine",
        tone === "warn" && "bg-gold/15 text-gold",
        tone === "danger" && "bg-ember/15 text-ember",
        tone === "neutral" && "bg-ink/5 text-ink/70",
      )}
    >
      {label}
    </span>
  );
}
