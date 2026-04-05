import type { NotificationSettings } from "../../api/types";
import SettingsSectionEditor, { type SettingsFieldConfig } from "./SettingsSectionEditor";

const fields: SettingsFieldConfig[] = [
  { key: "browser_notifications", label: "Browser notifications", description: "Allow in-app browser notifications.", type: "boolean" },
  { key: "notify_trade_executed", label: "Notify on trade execution", description: "Push an alert after each execution.", type: "boolean" },
  { key: "notify_circuit_breaker", label: "Notify on circuit breaker", description: "Alert when a risk breaker trips.", type: "boolean" },
  { key: "notify_daily_summary", label: "Daily summary notifications", description: "Send a local end-of-day recap.", type: "boolean" },
  { key: "notify_paper_milestone", label: "Paper milestone notifications", description: "Notify when paper-trading milestones are reached.", type: "boolean" },
];

export default function NotificationSettingsPanel({
  settings,
  saving,
  onSave,
}: {
  settings: NotificationSettings;
  saving: boolean;
  onSave: (patch: Record<string, unknown>) => Promise<void>;
}) {
  return (
    <SettingsSectionEditor
      eyebrow="Settings"
      fields={fields}
      note="Browser notifications are the only notification channel exposed in the app right now."
      onSave={onSave}
      saving={saving}
      sectionKey="notifications"
      title="Notifications"
      values={settings as unknown as Record<string, string | number | boolean>}
    />
  );
}
