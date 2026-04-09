import { useEffect, useMemo, useState, useTransition } from "react";
import type {
  ProviderGuide,
  SaveSetupSecretsResponse,
  SecretKeyStatus,
  ServiceGuide,
  SetupGuidesResponse,
  SetupStatus,
} from "../../api/types";
import Panel from "../common/Panel";
import ThinkingDots from "../common/ThinkingDots";
import StatusBadge from "../common/StatusBadge";


const PROVIDER_STATUS_LABELS: Record<ProviderGuide["id"], string> = {
  openai: "OpenAI",
  anthropic: "Anthropic",
  google: "Google",
  ollama: "Ollama",
};

const SERVICE_STATUS_LABELS: Record<string, string> = {
  alpaca: "Alpaca",
  finnhub: "Finnhub",
  marketaux: "Marketaux",
  fmp: "FMP",
  fred: "FRED",
  reddit: "Reddit",
  polygon: "Polygon",
};

interface ApiKeyStepProps {
  guides: SetupGuidesResponse;
  keys: SecretKeyStatus[];
  status: SetupStatus;
  loading: boolean;
  saving: boolean;
  error: string | null;
  focusService?: string | null;
  onSave: (payload: {
    ai_provider: "openai" | "anthropic" | "google" | "ollama";
    alpaca_mode: "paper" | "live";
    values: Record<string, string>;
  }) => Promise<SaveSetupSecretsResponse>;
}

function Field({
  envKey,
  label,
  placeholder,
  value,
  onChange,
}: {
  envKey: string;
  label: string;
  placeholder: string;
  value: string;
  onChange: (next: string) => void;
}) {
  return (
    <label className="grid gap-2">
      <span className="text-sm font-semibold text-ink">{label}</span>
      <input
        autoCapitalize="none"
        autoComplete="new-password"
        spellCheck={false}
        className="rounded-2xl border border-ink/10 bg-white px-4 py-3 text-sm text-ink outline-none transition focus:border-tide/40 focus:ring-2 focus:ring-tide/15"
        name={envKey}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        type={envKey.includes("KEY") || envKey.includes("SECRET") || envKey.includes("TOKEN") ? "password" : "text"}
        value={value}
      />
    </label>
  );
}

function GuideStatus({
  configured,
  maskedValue,
  fallback,
  detail,
}: {
  configured: boolean;
  maskedValue?: string;
  fallback: string;
  detail: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-2xl bg-slate px-4 py-3">
      <StatusBadge label={configured ? "configured" : fallback} tone={configured ? "good" : "warn"} />
      <span className="text-sm text-ink/65">{configured ? maskedValue || "stored locally" : detail}</span>
    </div>
  );
}

function ServiceCard({
  guide,
  status,
  draft,
  setDraftValue,
  alpacaMode,
  setAlpacaMode,
  focusService,
}: {
  guide: ServiceGuide;
  status?: SecretKeyStatus;
  draft: Record<string, string>;
  setDraftValue: (key: string, value: string) => void;
  alpacaMode: "paper" | "live";
  setAlpacaMode: (value: "paper" | "live") => void;
  focusService?: string | null;
}) {
  const statusDetail =
    guide.id === "alpaca"
      ? "Required if you want FinPilot to place paper or live trades through Alpaca."
      : "Optional until you want this data source active in your signals.";
  const isFocused = focusService === guide.id;

  return (
    <details
      className={`rounded-[24px] border bg-white/85 p-4 open:shadow-soft ${
        isFocused ? "border-tide/35 ring-2 ring-tide/15" : "border-ink/8"
      }`}
      id={`setup-service-${guide.id}`}
      open={guide.id === "alpaca" || isFocused}
    >
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-display text-xl text-ink">{guide.label}</span>
            {guide.recommended ? <StatusBadge label="recommended" tone="good" /> : null}
          </div>
          <p className="mt-1 text-sm text-ink/65">{guide.description}</p>
        </div>
        <StatusBadge
          label={status?.configured ? "ready" : guide.category.replace("_", " ")}
          tone={status?.configured ? "good" : "neutral"}
        />
      </summary>
      <div className="mt-4 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-3">
          <GuideStatus
            configured={Boolean(status?.configured)}
            fallback={status?.message ?? "optional"}
            maskedValue={status?.masked_value}
            detail={statusDetail}
          />
          <div className="rounded-2xl bg-ink/5 px-4 py-3 text-sm text-ink/75">{guide.helper_text}</div>
          <ol className="grid gap-2 text-sm text-ink/80">
            {guide.instructions.map((step) => (
              <li key={step} className="rounded-2xl bg-slate px-4 py-3">
                {step}
              </li>
            ))}
          </ol>
          <a
            className="inline-flex rounded-full border border-ink/10 px-4 py-2 text-sm font-semibold text-ink transition hover:border-tide/40 hover:bg-white"
            href={guide.setup_url}
            rel="noreferrer"
            target="_blank"
          >
            Open official setup page
          </a>
        </div>
        <div className="grid content-start gap-3">
          {guide.id === "alpaca" ? (
            <div className="grid gap-2 rounded-2xl bg-slate p-4">
              <div className="text-sm font-semibold text-ink">Alpaca mode</div>
              <div className="grid gap-2 sm:grid-cols-2">
                {(["paper", "live"] as const).map((value) => (
                  <button
                    key={value}
                    className={`rounded-2xl border px-4 py-3 text-left text-sm transition ${
                      alpacaMode === value
                        ? "border-tide/40 bg-white text-ink shadow-soft"
                        : "border-transparent bg-white/70 text-ink/65"
                    }`}
                    onClick={() => setAlpacaMode(value)}
                    type="button"
                  >
                    <div className="font-semibold capitalize">{value}</div>
                    <div className="mt-1 text-xs text-ink/55">
                      {value === "paper" ? "Recommended for every new setup." : "Leave off until you intentionally unlock live trading."}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ) : null}
          {guide.env_keys.map((envKey) => (
            <Field
              key={envKey}
              envKey={envKey}
              label={envKey}
              onChange={(next) => setDraftValue(envKey, next)}
              placeholder={envKey === "REDDIT_USER_AGENT" ? "finpilot:v0.1 (by /u/your_username)" : `Paste ${envKey.toLowerCase()} here`}
              value={draft[envKey] ?? ""}
            />
          ))}
        </div>
      </div>
    </details>
  );
}

export default function ApiKeyStep({
  guides,
  keys,
  status,
  saving,
  error,
  focusService,
  onSave,
}: ApiKeyStepProps) {
  const [selectedProvider, setSelectedProvider] = useState<ProviderGuide["id"]>(
    (status.ai_provider as ProviderGuide["id"] | undefined) ?? "openai",
  );
  const [alpacaMode, setAlpacaMode] = useState<"paper" | "live">(
    status.alpaca_mode === "live" ? "live" : "paper",
  );
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");
  const [localError, setLocalError] = useState("");
  const [isPending, startTransition] = useTransition();

  const keyStatusMap = useMemo(() => new Map(keys.map((key) => [key.name, key])), [keys]);
  const selectedGuide = useMemo(
    () => guides.providers.find((provider) => provider.id === selectedProvider) ?? guides.providers[0],
    [guides.providers, selectedProvider],
  );
  const selectedProviderDetail = useMemo(() => {
    if (selectedGuide.id === "ollama") {
      return "No API key is needed. Install Ollama locally and pull the model you want FinPilot to use.";
    }
    return `Required before FinPilot can use ${selectedGuide.label} for strategy chat and agent analysis.`;
  }, [selectedGuide]);

  const setDraftValue = (envKey: string, value: string) => {
    setDraft((current) => ({ ...current, [envKey]: value }));
  };

  useEffect(() => {
    if (!focusService) {
      return;
    }

    const element = document.getElementById(`setup-service-${focusService}`);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [focusService]);

  const submit = async () => {
    setMessage("");
    setLocalError("");

    if (selectedGuide.needs_api_key && selectedGuide.env_key) {
      const existingProviderStatus = keyStatusMap.get(PROVIDER_STATUS_LABELS[selectedProvider]);
      const hasFreshValue = Boolean(draft[selectedGuide.env_key]?.trim());
      if (!hasFreshValue && !existingProviderStatus?.configured) {
        setLocalError(`Add ${selectedGuide.label} before saving this provider.`);
        return;
      }
    }

    try {
      const response = await onSave({
        ai_provider: selectedProvider,
        alpaca_mode: alpacaMode,
        values: Object.fromEntries(Object.entries(draft).filter(([, value]) => value.trim() !== "")),
      });
      setDraft({});
      setMessage(response.message);
    } catch (saveError) {
      setLocalError(saveError instanceof Error ? saveError.message : "Unable to save your local setup.");
    }
  };

  return (
    <Panel
      title="Local onboarding"
      eyebrow="Step 1"
      action={<StatusBadge label={status.has_ai_provider ? "AI ready" : "choose one AI provider"} tone={status.has_ai_provider ? "good" : "warn"} />}
    >
      <div className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
        <div className="space-y-4">
          <p className="text-sm leading-6 text-ink/75">
            FinPilot now creates <code>.env</code> for you and opens this app immediately. Add one AI provider to get started, keep Alpaca in paper mode, and layer in optional data sources whenever you want more signal depth.
          </p>
          <div className="rounded-[24px] border border-tide/15 bg-white px-5 py-4">
            <div className="font-mono text-[11px] uppercase tracking-[0.3em] text-tide/70">Security posture</div>
            <p className="mt-2 text-sm leading-6 text-ink/75">{guides.security_note}</p>
          </div>
          <div className="grid gap-3">
            {guides.quickstart_steps.map((step, index) => (
              <div key={step} className="flex gap-3 rounded-2xl bg-slate px-4 py-3 text-sm text-ink/80">
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-white font-mono text-xs text-ink/65">
                  {index + 1}
                </div>
                <div>{step}</div>
              </div>
            ))}
          </div>
          <div className="grid gap-3">
            {keys.map((key) => (
              <div key={key.name} className="flex items-center justify-between rounded-2xl bg-ink/5 px-4 py-3">
                <div>
                  <div className="font-semibold">{key.name}</div>
                  <div className="text-sm text-ink/60">{key.masked_value || "not configured"}</div>
                </div>
                <StatusBadge label={key.configured ? "configured" : key.message} tone={key.configured ? "good" : "warn"} />
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-[28px] bg-white/75 p-4 shadow-soft">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <div className="font-mono text-[11px] uppercase tracking-[0.3em] text-tide/70">Start here</div>
                <h4 className="font-display text-2xl text-ink">Pick your AI provider</h4>
              </div>
              <StatusBadge label={selectedGuide.label} tone="neutral" />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {guides.providers.map((provider) => {
                const currentStatus = keyStatusMap.get(PROVIDER_STATUS_LABELS[provider.id]);
                const active = provider.id === selectedProvider;
                return (
                  <button
                    key={provider.id}
                    className={`rounded-[24px] border px-4 py-4 text-left transition ${
                      active ? "border-tide/40 bg-slate shadow-soft" : "border-white/70 bg-white/70"
                    }`}
                    onClick={() => setSelectedProvider(provider.id)}
                    type="button"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold text-ink">{provider.label}</span>
                      {provider.recommended ? <StatusBadge label="recommended" tone="good" /> : null}
                      {currentStatus?.configured ? <StatusBadge label="configured" tone="neutral" /> : null}
                    </div>
                    <p className="mt-2 text-sm leading-6 text-ink/70">{provider.description}</p>
                  </button>
                );
              })}
            </div>
            <div className="mt-4 grid gap-4 rounded-[24px] bg-slate p-4 lg:grid-cols-[1fr_0.95fr]">
              <div className="space-y-3">
                <GuideStatus
                  configured={Boolean(keyStatusMap.get(PROVIDER_STATUS_LABELS[selectedProvider])?.configured)}
                  fallback={selectedGuide.needs_api_key ? "missing" : "local model"}
                  maskedValue={keyStatusMap.get(PROVIDER_STATUS_LABELS[selectedProvider])?.masked_value}
                  detail={selectedProviderDetail}
                />
                <div className="rounded-2xl bg-white/80 px-4 py-3 text-sm text-ink/75">{selectedGuide.helper_text}</div>
                <ol className="grid gap-2 text-sm text-ink/80">
                  {selectedGuide.instructions.map((step) => (
                    <li key={step} className="rounded-2xl bg-white/80 px-4 py-3">
                      {step}
                    </li>
                  ))}
                </ol>
                <a
                  className="inline-flex rounded-full border border-ink/10 px-4 py-2 text-sm font-semibold text-ink transition hover:border-tide/40 hover:bg-white"
                  href={selectedGuide.setup_url}
                  rel="noreferrer"
                  target="_blank"
                >
                  Open official provider page
                </a>
              </div>
              <div className="grid content-start gap-3">
                {selectedGuide.needs_api_key && selectedGuide.env_key ? (
                  <Field
                    envKey={selectedGuide.env_key}
                    label={selectedGuide.env_key}
                    onChange={(next) => setDraftValue(selectedGuide.env_key ?? "", next)}
                    placeholder={`Paste ${selectedGuide.label} API key here`}
                    value={draft[selectedGuide.env_key] ?? ""}
                  />
                ) : (
                  <div className="rounded-2xl border border-ink/10 bg-white px-4 py-4 text-sm leading-6 text-ink/75">
                    No hosted API key is needed for Ollama. If Ollama is installed locally, you can save this choice and continue.
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="space-y-4">
            {guides.services.map((guide) => (
              <ServiceCard
                key={guide.id}
                alpacaMode={alpacaMode}
                draft={draft}
                focusService={focusService}
                guide={guide}
                setAlpacaMode={setAlpacaMode}
                setDraftValue={setDraftValue}
                status={keyStatusMap.get(SERVICE_STATUS_LABELS[guide.id])}
              />
            ))}
          </div>

          <div className="rounded-[24px] border border-ink/8 bg-ink px-5 py-4 text-white shadow-soft">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="space-y-2">
                <div className="font-display text-2xl">Save onboarding details locally</div>
                <p className="text-sm text-white/75">
                  This writes your selections into the local <code>.env</code> file and refreshes masked status in the app.
                </p>
                {message ? <p className="text-sm text-emerald-200">{message}</p> : null}
                {localError || error ? <p className="text-sm text-amber-200">{localError || error}</p> : null}
              </div>
              <button
                className="rounded-full bg-white px-5 py-3 text-sm font-semibold text-ink disabled:cursor-not-allowed disabled:opacity-60"
                disabled={saving || isPending}
                onClick={() => startTransition(() => void submit())}
                type="button"
              >
                {saving || isPending ? <ThinkingDots className="text-ink" /> : "Save to .env"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Panel>
  );
}
