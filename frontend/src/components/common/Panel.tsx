import type { PropsWithChildren, ReactNode } from "react";
import clsx from "clsx";

interface PanelProps extends PropsWithChildren {
  title?: string;
  eyebrow?: string;
  action?: ReactNode;
  className?: string;
}

export default function Panel({ title, eyebrow, action, className, children }: PanelProps) {
  return (
    <section
      className={clsx(
        "rounded-[28px] border border-white/70 bg-white/80 p-5 shadow-soft backdrop-blur-sm",
        className,
      )}
    >
      {(title || eyebrow || action) && (
        <div className="mb-5 flex items-start justify-between gap-3">
          <div>
            {eyebrow ? (
              <div className="mb-1 font-mono text-[10px] font-semibold uppercase tracking-[0.35em] text-tide/60">
                {eyebrow}
              </div>
            ) : null}
            {title ? (
              <h3 className="font-display text-xl leading-tight text-ink">{title}</h3>
            ) : null}
          </div>
          {action ? <div className="shrink-0">{action}</div> : null}
        </div>
      )}
      {children}
    </section>
  );
}
