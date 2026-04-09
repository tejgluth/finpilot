import { useState } from "react";
import { api } from "../../api/client";
import Panel from "../common/Panel";
import ThinkingDots from "../common/ThinkingDots";

export default function KillSwitch({
  active,
  onChanged,
}: {
  active: boolean;
  onChanged?: () => void;
}) {
  const [saving, setSaving] = useState(false);

  const toggle = async () => {
    setSaving(true);
    try {
      const next = !active;
      await api.setKillSwitch(next, next ? "User-triggered emergency halt." : "");
      await onChanged?.();
    } finally {
      setSaving(false);
    }
  };

  return (
    <Panel title="Emergency halt" eyebrow="Kill switch">
      <button
        className={`rounded-full px-6 py-4 text-sm font-semibold ${active ? "bg-ink text-white" : "bg-ember text-white"}`}
        onClick={() => void toggle()}
        disabled={saving}
      >
        {saving ? <ThinkingDots className="text-white" /> : active ? "Resume system" : "Activate kill switch"}
      </button>
    </Panel>
  );
}
