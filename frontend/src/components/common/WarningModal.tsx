import type { PropsWithChildren } from "react";

interface WarningModalProps extends PropsWithChildren {
  title: string;
  open: boolean;
  onClose: () => void;
}

export default function WarningModal({ title, open, onClose, children }: WarningModalProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-ink/40 p-4">
      <div className="w-full max-w-lg rounded-[28px] bg-white p-6 shadow-soft">
        <div className="flex items-center justify-between gap-4">
          <h3 className="font-display text-2xl text-ink">{title}</h3>
          <button className="rounded-full bg-slate px-3 py-1 text-sm" onClick={onClose}>
            Close
          </button>
        </div>
        <div className="mt-4 text-sm text-ink/75">{children}</div>
      </div>
    </div>
  );
}
