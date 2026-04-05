import type { LlmSettings } from "../../api/types";
import SettingsSectionEditor, { type SettingsFieldConfig } from "./SettingsSectionEditor";

const fields: SettingsFieldConfig[] = [
  {
    key: "provider",
    label: "Provider",
    description: "Provider changes apply on the next app run.",
    type: "select",
    options: [
      { label: "OpenAI", value: "openai" },
      { label: "Anthropic", value: "anthropic" },
      { label: "Google", value: "google" },
      { label: "Ollama", value: "ollama" },
    ],
  },
  {
    key: "model",
    label: "Model",
    description: "Leave blank to use the provider default.",
    type: "text",
    placeholder: "provider default",
  },
  {
    key: "temperature_analysis",
    label: "Analysis temperature",
    description: "Lower keeps financial analysis tighter and more factual.",
    type: "number",
    min: 0,
    max: 1,
    step: 0.05,
  },
  {
    key: "temperature_strategy",
    label: "Strategy chat temperature",
    description: "Higher is more exploratory when brainstorming strategies.",
    type: "number",
    min: 0,
    max: 1,
    step: 0.05,
  },
  {
    key: "max_tokens_per_request",
    label: "Max tokens per request",
    description: "Ceiling for a single model call.",
    type: "number",
    min: 256,
    step: 256,
  },
  {
    key: "max_cost_per_session_usd",
    label: "Max session cost (USD)",
    description: "Soft budget cap for one session.",
    type: "number",
    min: 0,
    step: 0.1,
  },
  {
    key: "show_token_usage_in_ui",
    label: "Show token usage in UI",
    description: "Keep usage/cost context visible while you work.",
    type: "boolean",
  },
  {
    key: "ollama_base_url",
    label: "Ollama base URL",
    description: "Local endpoint used when the provider is Ollama.",
    type: "text",
    placeholder: "http://localhost:11434",
  },
  {
    key: "ollama_model",
    label: "Ollama model",
    description: "Model name already pulled into your local Ollama install.",
    type: "text",
    placeholder: "llama3.2",
  },
];

export default function LlmSettingsPanel({
  settings,
  saving,
  onSave,
}: {
  settings: LlmSettings;
  saving: boolean;
  onSave: (patch: Record<string, unknown>) => Promise<void>;
}) {
  return (
    <SettingsSectionEditor
      eyebrow="Settings"
      fields={fields}
      note="Hosted providers need their matching key in your local .env. Ollama only needs a running local model."
      onSave={onSave}
      saving={saving}
      sectionKey="llm"
      title="LLM provider"
      values={settings as unknown as Record<string, string | number | boolean>}
    />
  );
}
