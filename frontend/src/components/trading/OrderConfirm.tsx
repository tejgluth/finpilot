import type { PropsWithChildren } from "react";

import WarningModal from "../common/WarningModal";

interface OrderConfirmProps extends PropsWithChildren {
  open: boolean;
  title?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function OrderConfirm({
  open,
  title = "Confirm order",
  onConfirm,
  onCancel,
  children,
}: OrderConfirmProps) {
  return (
    <WarningModal title={title} open={open} onClose={onCancel}>
      <div className="space-y-4">
        <div>{children}</div>
        <div className="flex gap-3">
          <button className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white" onClick={onConfirm}>
            Confirm
          </button>
          <button className="rounded-full bg-slate px-4 py-2 text-sm" onClick={onCancel}>
            Cancel
          </button>
        </div>
      </div>
    </WarningModal>
  );
}
