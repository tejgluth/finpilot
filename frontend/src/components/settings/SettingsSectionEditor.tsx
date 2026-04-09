import { useEffect, useMemo, useState, useTransition } from "react";
import Panel from "../common/Panel";
import ThinkingDots from "../common/ThinkingDots";

type SettingsValue = string | number | boolean;

export interface SettingsFieldOption {
  label: string;
  value: string;
}

export interface SettingsFieldConfig {
  key: string;
  label: string;
  description?: string;
  type: "text" | "number" | "boolean" | "select";
  placeholder?: string;
  min?: number;
  max?: number;
  step?: number;
  options?: SettingsFieldOption[];
  secret?: boolean;
}

interface SettingsSectionEditorProps {
  title: string;
  eyebrow: string;
  note?: string;
  sectionKey: string;
  highlightKey?: string | null;
  values: Record<string, SettingsValue>;
  fields: SettingsFieldConfig[];
  saving: boolean;
  onSave: (patch: Record<string, unknown>) => Promise<void>;
}

function fieldsToDraft(
  values: Record<string, SettingsValue>,
  fields: SettingsFieldConfig[],
): Record<string, SettingsValue> {
  return Object.fromEntries(fields.map((field) => [field.key, values[field.key]]));
}

function formatValue(value: SettingsValue) {
  return typeof value === "boolean" ? (value ? "Enabled" : "Disabled") : String(value);
}

export default function SettingsSectionEditor({
  title,
  eyebrow,
  note,
  sectionKey,
  highlightKey,
  values,
  fields,
  saving,
  onSave,
}: SettingsSectionEditorProps) {
  const [draft, setDraft] = useState<Record<string, SettingsValue>>(() => fieldsToDraft(values, fields));
  const [message, setMessage] = useState("");
  const [localError, setLocalError] = useState("");
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    setDraft(fieldsToDraft(values, fields));
  }, [values, fields]);

  useEffect(() => {
    if (!highlightKey) {
      return;
    }

    const element = document.getElementById(`settings-field-${sectionKey}-${highlightKey}`);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [highlightKey, sectionKey]);

  const dirty = useMemo(
    () => fields.some((field) => draft[field.key] !== values[field.key]),
    [draft, fields, values],
  );

  const busy = saving || isPending;

  const updateValue = (key: string, value: SettingsValue) => {
    setDraft((current) => ({ ...current, [key]: value }));
  };

  const submit = () => {
    setMessage("");
    setLocalError("");
    startTransition(() => {
      void onSave({ [sectionKey]: draft })
        .then(() => {
          setMessage("Saved.");
        })
        .catch((error) => {
          setLocalError(error instanceof Error ? error.message : "Unable to save settings.");
        });
    });
  };

  const reset = () => {
    setDraft(fieldsToDraft(values, fields));
    setMessage("");
    setLocalError("");
  };

  return (
    <Panel title={title} eyebrow={eyebrow}>
      {note ? <p className="mb-4 text-sm leading-6 text-ink/70">{note}</p> : null}

      <div className="grid gap-4 md:grid-cols-2">
        {fields.map((field) => {
          const value = draft[field.key];
          const isHighlighted = highlightKey === field.key;

          return (
            <label
              key={field.key}
              className={`grid gap-2 rounded-[24px] px-4 py-4 ${
                isHighlighted ? "bg-tide/8 ring-2 ring-tide/20" : "bg-slate"
              }`}
              id={`settings-field-${sectionKey}-${field.key}`}
            >
              <div className="space-y-1">
                <div className="font-semibold text-ink">{field.label}</div>
                {field.description ? <div className="text-sm leading-5 text-ink/60">{field.description}</div> : null}
              </div>

              {field.type === "boolean" ? (
                <button
                  className={`flex items-center justify-between rounded-2xl border px-4 py-3 text-left text-sm transition ${
                    value
                      ? "border-tide/35 bg-white text-ink shadow-soft"
                      : "border-transparent bg-white/70 text-ink/70"
                  }`}
                  onClick={() => updateValue(field.key, !Boolean(value))}
                  type="button"
                >
                  <span>{formatValue(value)}</span>
                  <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-ink/45">
                    {Boolean(value) ? "On" : "Off"}
                  </span>
                </button>
              ) : field.type === "select" ? (
                <select
                  className="rounded-2xl border border-ink/10 bg-white px-4 py-3 text-sm text-ink outline-none transition focus:border-tide/40 focus:ring-2 focus:ring-tide/15"
                  onChange={(event) => updateValue(field.key, event.target.value)}
                  value={String(value)}
                >
                  {field.options?.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  className="rounded-2xl border border-ink/10 bg-white px-4 py-3 text-sm text-ink outline-none transition focus:border-tide/40 focus:ring-2 focus:ring-tide/15"
                  max={field.max}
                  min={field.min}
                  onChange={(event) => {
                    if (field.type === "number") {
                      const next = event.target.value;
                      updateValue(field.key, next === "" ? 0 : Number(next));
                      return;
                    }
                    updateValue(field.key, event.target.value);
                  }}
                  placeholder={field.placeholder}
                  step={field.step}
                  type={field.secret ? "password" : field.type}
                  value={field.type === "number" ? String(value) : String(value)}
                />
              )}
            </label>
          );
        })}
      </div>

      <div className="mt-4 flex flex-col gap-3 rounded-[24px] border border-ink/8 bg-white px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="text-sm text-ink/65">
          {message ? <span className="text-pine">{message}</span> : dirty ? "Unsaved changes in this section." : "No unsaved changes."}
          {localError ? <span className="block text-ember">{localError}</span> : null}
        </div>
        <div className="flex gap-3">
          <button
            className="rounded-full border border-ink/10 px-4 py-2 text-sm font-semibold text-ink disabled:cursor-not-allowed disabled:opacity-50"
            disabled={!dirty || busy}
            onClick={reset}
            type="button"
          >
            Reset
          </button>
          <button
            className="rounded-full bg-ink px-5 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
            disabled={!dirty || busy}
            onClick={submit}
            type="button"
          >
            {busy ? <ThinkingDots className="text-white" /> : "Save changes"}
          </button>
        </div>
      </div>
    </Panel>
  );
}
