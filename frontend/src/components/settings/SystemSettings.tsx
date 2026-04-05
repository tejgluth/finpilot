import type { SystemSettings } from "../../api/types";
import SettingsSectionEditor, { type SettingsFieldConfig } from "./SettingsSectionEditor";

const fields: SettingsFieldConfig[] = [
  { key: "backend_port", label: "Backend port", description: "Port the local API binds to on next run.", type: "number", min: 1, step: 1 },
  { key: "frontend_port", label: "Frontend port", description: "Port the web app uses on next run.", type: "number", min: 1, step: 1 },
  { key: "db_path", label: "Database path", description: "SQLite file used for local state and audit history.", type: "text", placeholder: "./data/finpilot.db" },
  { key: "cache_dir", label: "Cache directory", description: "Directory for local cache files.", type: "text", placeholder: "./data/cache" },
  { key: "artifacts_dir", label: "Artifacts directory", description: "Where backtest artifacts are stored.", type: "text", placeholder: "./data/artifacts" },
  { key: "audit_log_path", label: "Audit log path", description: "Flat-file audit log location.", type: "text", placeholder: "./data/audit.log" },
  { key: "debug_logging", label: "Debug logging", description: "Expose more verbose local logs.", type: "boolean" },
];

export default function SystemSettingsPanel({
  settings,
  saving,
  onSave,
}: {
  settings: SystemSettings;
  saving: boolean;
  onSave: (patch: Record<string, unknown>) => Promise<void>;
}) {
  return (
    <SettingsSectionEditor
      eyebrow="Settings"
      fields={fields}
      note="System path and port changes are persisted immediately but usually take effect the next time you start the app."
      onSave={onSave}
      saving={saving}
      sectionKey="system"
      title="System"
      values={settings as unknown as Record<string, string | number | boolean>}
    />
  );
}
