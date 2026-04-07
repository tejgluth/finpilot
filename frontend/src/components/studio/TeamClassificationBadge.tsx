import clsx from "clsx";
import type { TeamClassification } from "../../api/types";

interface Props {
  classification: TeamClassification | undefined;
  size?: "sm" | "md";
}

const CONFIG: Record<
  TeamClassification,
  { label: string; className: string }
> = {
  premade: {
    label: "Premade",
    className: "bg-pine/10 text-pine ring-1 ring-pine/30",
  },
  validated_custom: {
    label: "Custom",
    className: "bg-tide/10 text-tide ring-1 ring-tide/30",
  },
  experimental_custom: {
    label: "Experimental",
    className: "bg-amber-100 text-amber-700 ring-1 ring-amber-300",
  },
};

export default function TeamClassificationBadge({ classification, size = "sm" }: Props) {
  if (!classification) return null;
  const cfg = CONFIG[classification];
  if (!cfg) return null;

  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full font-mono font-semibold tracking-wide",
        size === "sm" ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-xs",
        cfg.className,
      )}
    >
      {cfg.label}
    </span>
  );
}
