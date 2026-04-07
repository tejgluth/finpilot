import type {
  AgentMetadata,
  AlpacaPlanResponse,
  ArchitectureDraft,
  ArchitectureConversationTurn,
  ArchitectureIntent,
  ArchitecturePatch,
  AuditEntry,
  CapabilityGap,
  BacktestResult,
  CompiledTeam,
  ConversationRequirement,
  CustomConversation,
  NodeModeEligibility,
  PermissionsPayload,
  PortfolioPayload,
  PremadeTeamCatalog,
  PremadeTeamTemplate,
  SaveSetupSecretsResponse,
  SecretKeyStatus,
  SetupGuidesResponse,
  SetupStatus,
  StrategyConversation,
  StrategyDraft,
  StrategyPreferences,
  TeamComparison,
  TeamRecommendation,
  TeamTopology,
  TeamValidationResult,
  TeamVersion,
  TradeOrderResponse,
  TradingStatusPayload,
  UserSettings,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const target =
    API_BASE === "/api" && path.startsWith("/api/")
      ? path
      : `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;

  const response = await fetch(target, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });
  if (!response.ok) {
    const rawBody = await response.text();
    try {
      const parsed = JSON.parse(rawBody) as { detail?: string };
      throw new Error(parsed.detail || `${response.status} ${response.statusText}`);
    } catch {
      throw new Error(rawBody || `${response.status} ${response.statusText}`);
    }
  }
  return response.json() as Promise<T>;
}

export const api = {
  getSetupStatus: () => request<SetupStatus>("/api/setup/status"),
  getPlan: () => request<AlpacaPlanResponse>("/api/setup/plan"),
  validateKeys: () => request<{ keys: SecretKeyStatus[] }>("/api/setup/validate-keys"),
  getSetupGuides: () => request<SetupGuidesResponse>("/api/setup/guides"),
  saveSetupSecrets: (payload: {
    ai_provider: "openai" | "anthropic" | "google" | "ollama";
    alpaca_mode: "paper" | "live";
    values: Record<string, string>;
  }) =>
    request<SaveSetupSecretsResponse>("/api/setup/save-secrets", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getSettings: () => request<UserSettings>("/api/settings/"),
  patchSettings: (patch: Record<string, unknown>) =>
    request<UserSettings>("/api/settings/", {
      method: "PATCH",
      body: JSON.stringify({ patch }),
    }),
  getAgents: async (): Promise<{ agents: AgentMetadata[] }> => {
    const payload = await request<{ descriptions: Record<string, string>; data_dependencies: Record<string, string[]> }>(
      "/api/agents",
    );
    return {
      agents: Object.entries(payload.descriptions).map(([name, description]) => ({
        name,
        description,
        data_dependencies: payload.data_dependencies[name] ?? [],
      })),
    };
  },
  listStrategyConversations: () => request<{ conversations: StrategyConversation[] }>("/api/strategy/conversations"),
  startStrategyConversation: (seedPrompt?: string) =>
    request<StrategyConversation>("/api/strategy/conversations", {
      method: "POST",
      body: JSON.stringify({ seed_prompt: seedPrompt ?? null }),
    }),
  getStrategyConversation: (conversationId: string) =>
    request<StrategyConversation>(`/api/strategy/conversations/${conversationId}`),
  sendStrategyMessage: (conversationId: string, content: string, requestCompile = false) =>
    request<{
      conversation: StrategyConversation;
      draft: StrategyDraft;
      compiled_team: CompiledTeam | null;
      comparison: TeamComparison | null;
      needs_follow_up: boolean;
    }>(`/api/strategy/conversations/${conversationId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content, request_compile: requestCompile }),
    }),
  compileStrategyConversation: (conversationId: string) =>
    request<{
      conversation: StrategyConversation;
      draft: StrategyDraft;
      compiled_team: CompiledTeam;
      comparison: TeamComparison;
      validation_report: { valid: boolean; warnings: string[]; normalized_fields: string[] };
    }>(`/api/strategy/conversations/${conversationId}/compile`, {
      method: "POST",
    }),
  saveStrategyTeam: (payload: { conversation_id?: string | null; compiled_team: CompiledTeam; label: string }) =>
    request<TeamVersion>("/api/strategy/teams", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getStrategyTeams: () => request<{ teams: TeamVersion[]; active_team: TeamVersion }>("/api/strategy/teams"),
  getDefaultTeam: () => request<TeamVersion>("/api/strategy/default-team"),
  getStrategyTeam: (teamId: string) => request<TeamVersion>(`/api/strategy/teams/${teamId}`),
  getStrategyTeamVersion: (teamId: string, versionNumber: number) =>
    request<TeamVersion>(`/api/strategy/teams/${teamId}/versions/${versionNumber}`),
  selectStrategyTeam: (teamId: string, versionNumber?: number) =>
    request<{ active_team_id: string; active_version_number: number }>(`/api/strategy/teams/${teamId}/select`, {
      method: "POST",
      body: JSON.stringify({ version_number: versionNumber ?? null }),
    }),
  compareStrategyTeam: (payload: { candidate_compiled_team?: CompiledTeam; team_id?: string; version_number?: number }) =>
    request<TeamComparison>("/api/strategy/compare", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getPremadeTeams: () => request<PremadeTeamCatalog>("/api/strategy/premade-teams"),
  getPremadeTeam: (teamId: string) => request<PremadeTeamTemplate>(`/api/strategy/premade-teams/${teamId}`),
  compilePremadeTeam: (teamId: string) =>
    request<{ compiled_team: CompiledTeam; comparison: TeamComparison }>(
      `/api/strategy/premade-teams/${teamId}/compile`,
      { method: "POST" },
    ),
  matchTeam: (preferences: Partial<StrategyPreferences>) =>
    request<TeamRecommendation>("/api/strategy/match-team", {
      method: "POST",
      body: JSON.stringify(preferences),
    }),
  analyzeTicker: (payload: Record<string, unknown>) =>
    request<{
      signals: unknown[];
      bull_case: Record<string, unknown> | null;
      bear_case: Record<string, unknown> | null;
      decision: Record<string, unknown>;
      execution_snapshot: Record<string, unknown>;
    }>("/api/agents/analyze", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  runBacktest: (payload: Record<string, unknown>) =>
    request<BacktestResult>("/api/backtest/run", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  streamBacktest: async (
    payload: Record<string, unknown>,
    handlers: {
      onProgress?: (event: Record<string, unknown>) => void;
      onComplete: (result: BacktestResult) => void;
      onError?: (message: string) => void;
    },
  ) => {
    const target = API_BASE === "/api" ? "/api/backtest/stream" : `${API_BASE}/api/backtest/stream`;
    const response = await fetch(target, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok || !response.body) {
      const rawBody = await response.text();
      throw new Error(rawBody || `Unable to start backtest stream (${response.status}).`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    const processMessage = (message: string) => {
      const lines = message.split(/\r?\n/);
      let eventName = "message";
      const dataLines: string[] = [];

      for (const line of lines) {
        if (line.startsWith("event:")) {
          eventName = line.slice("event:".length).trim();
        } else if (line.startsWith("data:")) {
          dataLines.push(line.slice("data:".length).trimStart());
        }
      }

      if (!dataLines.length) {
        return;
      }

      const parsed = JSON.parse(dataLines.join("\n")) as Record<string, unknown>;
      if (eventName === "progress") {
        handlers.onProgress?.(parsed);
      } else if (eventName === "complete") {
        handlers.onComplete(parsed as unknown as BacktestResult);
      } else if (eventName === "error") {
        handlers.onError?.(String(parsed.detail ?? "Backtest stream failed."));
      }
    };

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        const trailing = buffer.trim();
        if (trailing) {
          processMessage(trailing);
        }
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      const messages = buffer.split(/\r?\n\r?\n/);
      buffer = messages.pop() ?? "";

      for (const message of messages) {
        processMessage(message);
      }
    }
  },
  getPortfolio: () => request<PortfolioPayload>("/api/portfolio/"),
  getPermissions: () => request<PermissionsPayload>("/api/permissions/"),
  updatePermissions: (level: string) =>
    request<{ level: string }>("/api/permissions", {
      method: "PATCH",
      body: JSON.stringify({ level }),
    }),
  acknowledgeRisks: (acceptedItemIds: string[]) =>
    request<{ ok: boolean; acknowledged: boolean }>("/api/permissions/acknowledge-risks", {
      method: "POST",
      body: JSON.stringify({ accepted_ids: acceptedItemIds }),
    }),
  getTradingStatus: () => request<TradingStatusPayload>("/api/trading/status"),
  setLiveTradingEnabled: (enabled: boolean) =>
    request<{ enabled: boolean; live_unlock: Record<string, unknown> }>("/api/trading/live-enable", {
      method: "POST",
      body: JSON.stringify({ enabled }),
    }),
  submitOrder: (payload: {
    ticker: string;
    action: "BUY" | "SELL";
    notional_usd: number;
    confirm?: boolean;
    reasoning?: string;
    team_id?: string | null;
    execution_snapshot_id?: string | null;
  }) =>
    request<TradeOrderResponse>("/api/trading/order", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  setKillSwitch: (active: boolean, reason = "") =>
    request<{ active: boolean; reason: string }>("/api/trading/kill-switch", {
      method: "POST",
      body: JSON.stringify({ active, reason }),
    }),
  getAudit: (limit = 100) => request<{ entries: AuditEntry[] }>(`/api/audit/?limit=${limit}`),

  // ── Custom Team ───────────────────────────────────────────────────────────
  customTeam: {
    listConversations: () =>
      request<{ conversations: CustomConversation[] }>("/api/strategy/custom/conversations"),

    startConversation: (seedPrompt?: string) =>
      request<CustomConversation>("/api/strategy/custom/conversations", {
        method: "POST",
        body: JSON.stringify({ seed_prompt: seedPrompt ?? null }),
      }),

    getConversation: (conversationId: string) =>
      request<CustomConversation>(`/api/strategy/custom/conversations/${conversationId}`),

    sendMessage: (conversationId: string, content: string, requestCompile = false) =>
      request<{
        conversation: CustomConversation;
        draft: ArchitectureDraft;
        compiled_team: CompiledTeam | null;
        needs_follow_up: boolean;
        assistant_message: string;
        resolved_requirements: ConversationRequirement[];
        open_questions: ConversationRequirement[];
        graph_change_summary: string[];
        capability_gaps: CapabilityGap[];
        mode_compatibility: NodeModeEligibility;
        validation_state: ArchitectureConversationTurn["validation_state"];
      }>(`/api/strategy/custom/conversations/${conversationId}/messages`, {
        method: "POST",
        body: JSON.stringify({ content, request_compile: requestCompile }),
      }),

    compileConversation: (conversationId: string) =>
      request<{
        conversation: CustomConversation;
        draft: ArchitectureDraft;
        compiled_team: CompiledTeam;
        validation_result: TeamValidationResult;
        assistant_message: string;
        resolved_requirements: ConversationRequirement[];
        open_questions: ConversationRequirement[];
        graph_change_summary: string[];
        capability_gaps: CapabilityGap[];
        mode_compatibility: NodeModeEligibility;
        validation_state: ArchitectureConversationTurn["validation_state"];
      }>(`/api/strategy/custom/conversations/${conversationId}/compile`, {
        method: "POST",
      }),

    validateTopology: (topology: TeamTopology, intent?: Partial<ArchitectureIntent>) =>
      request<TeamValidationResult>("/api/strategy/custom/validate-topology", {
        method: "POST",
        body: JSON.stringify({ topology, intent: intent ?? null }),
      }),

    compileTopology: (
      topology: TeamTopology,
      intent?: Partial<ArchitectureIntent>,
      proposedName?: string,
      proposedDescription?: string,
    ) =>
      request<{ compiled_team: CompiledTeam; validation_result: TeamValidationResult }>(
        "/api/strategy/custom/compile-topology",
        {
          method: "POST",
          body: JSON.stringify({
            topology,
            intent: intent ?? null,
            proposed_name: proposedName ?? "Custom Team",
            proposed_description: proposedDescription ?? "",
          }),
        },
      ),

    generatePatch: (
      sourceTeamId: string,
      instruction: string,
      versionNumber?: number,
      compiledTeam?: CompiledTeam,
    ) =>
      request<ArchitecturePatch>("/api/strategy/custom/patch/generate", {
        method: "POST",
        body: JSON.stringify({
          source_team_id: sourceTeamId,
          source_version_number: versionNumber ?? null,
          instruction,
          compiled_team: compiledTeam ?? null,
        }),
      }),

    applyPatch: (
      patch: ArchitecturePatch,
      sourceTeamId: string,
      label: string,
      versionNumber?: number,
      compiledTeam?: CompiledTeam,
    ) =>
      request<{ compiled_team: CompiledTeam; validation_result: TeamValidationResult }>(
        "/api/strategy/custom/patch/apply",
        {
          method: "POST",
          body: JSON.stringify({
            source_team_id: sourceTeamId,
            source_version_number: versionNumber ?? null,
            patch,
            label,
            compiled_team: compiledTeam ?? null,
          }),
        },
      ),

    saveTeam: (payload: {
      conversation_id?: string | null;
      compiled_team: CompiledTeam;
      label: string;
    }) =>
      request<{ team_version: TeamVersion }>("/api/strategy/custom/teams", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  },
};
