import { create } from "zustand";
import { api } from "../api/client";
import type {
  CompiledAgentSpec,
  CompiledTeam,
  PremadeTeamCatalog,
  StrategyConversation,
  StrategyDraft,
  TeamComparison,
  TeamVersion,
} from "../api/types";

const ANALYSIS_AGENTS = [
  "fundamentals",
  "technicals",
  "sentiment",
  "macro",
  "value",
  "momentum",
  "growth",
] as const;

function cloneTeam(team: CompiledTeam | null): CompiledTeam | null {
  return team ? JSON.parse(JSON.stringify(team)) : null;
}

let hydrateRequestId = 0;

interface StrategyStore {
  conversation: StrategyConversation | null;
  draft: StrategyDraft | null;
  compiledTeam: CompiledTeam | null;
  comparison: TeamComparison | null;
  defaultTeam: TeamVersion | null;
  teams: TeamVersion[];
  activeTeam: TeamVersion | null;
  premadeCatalog: PremadeTeamCatalog | null;
  loading: boolean;
  saving: boolean;
  error: string | null;
  hydrate: () => Promise<void>;
  loadPremadeCatalog: () => Promise<void>;
  applyPremadeTeam: (teamId: string) => Promise<void>;
  sendMessage: (content: string, requestCompile?: boolean) => Promise<void>;
  compileDraft: () => Promise<void>;
  saveDraft: (label: string) => Promise<void>;
  selectTeam: (teamId: string, versionNumber?: number) => Promise<void>;
  updateDraftWeight: (agent: string, value: number) => Promise<void>;
  toggleDraftAgent: (agent: string, enabled: boolean) => Promise<void>;
  updateDraftRisk: (riskLevel: string) => Promise<void>;
  updateDraftHorizon: (timeHorizon: string) => Promise<void>;
  clearError: () => void;
}

export const useStrategyStore = create<StrategyStore>((set, get) => ({
  conversation: null,
  draft: null,
  compiledTeam: null,
  comparison: null,
  defaultTeam: null,
  teams: [],
  activeTeam: null,
  premadeCatalog: null,
  loading: false,
  saving: false,
  error: null,
  hydrate: async () => {
    const requestId = ++hydrateRequestId;
    set({ loading: true, error: null });
    try {
      const [defaultTeam, teamPayload, conversationPayload] = await Promise.all([
        api.getDefaultTeam(),
        api.getStrategyTeams(),
        api.listStrategyConversations(),
      ]);
      let conversation = conversationPayload.conversations[0] ?? null;
      if (!conversation) {
        conversation = await api.startStrategyConversation();
      }
      let compiledTeam: CompiledTeam | null = null;
      let comparison: TeamComparison | null = null;
      if (conversation.latest_draft) {
        try {
          const compiledPayload = await api.compileStrategyConversation(conversation.conversation_id);
          compiledTeam = compiledPayload.compiled_team;
          comparison = compiledPayload.comparison;
          conversation = compiledPayload.conversation;
        } catch {
          compiledTeam = null;
          comparison = null;
        }
      }
      if (requestId !== hydrateRequestId) return;
      set({
        defaultTeam,
        teams: teamPayload.teams,
        activeTeam: teamPayload.active_team,
        conversation,
        draft: conversation.latest_draft,
        compiledTeam,
        comparison,
        loading: false,
      });
    } catch (error) {
      if (requestId !== hydrateRequestId) return;
      set({ loading: false, error: error instanceof Error ? error.message : "Failed to load strategy state." });
    }
  },
  sendMessage: async (content, requestCompile = false) => {
    set({ loading: true, error: null });
    try {
      let conversation = get().conversation;
      if (!conversation) {
        conversation = await api.startStrategyConversation();
        set({ conversation });
      }
      const payload = await api.sendStrategyMessage(conversation.conversation_id, content, requestCompile);
      set({
        conversation: payload.conversation,
        draft: payload.draft,
        compiledTeam: cloneTeam(payload.compiled_team),
        comparison: payload.comparison,
        loading: false,
      });
    } catch (error) {
      set({ loading: false, error: error instanceof Error ? error.message : "Failed to send strategy message." });
    }
  },
  compileDraft: async () => {
    const conversation = get().conversation;
    if (!conversation) return;
    set({ loading: true, error: null });
    try {
      const payload = await api.compileStrategyConversation(conversation.conversation_id);
      set({
        conversation: payload.conversation,
        draft: payload.draft,
        compiledTeam: cloneTeam(payload.compiled_team),
        comparison: payload.comparison,
        loading: false,
      });
    } catch (error) {
      set({ loading: false, error: error instanceof Error ? error.message : "Failed to compile strategy draft." });
    }
  },
  saveDraft: async (label) => {
    const conversation = get().conversation;
    const compiledTeam = get().compiledTeam;
    if (!compiledTeam) return;
    set({ saving: true, error: null });
    try {
      await api.saveStrategyTeam({
        conversation_id: conversation?.conversation_id ?? null,
        compiled_team: compiledTeam,
        label,
      });
      const teamPayload = await api.getStrategyTeams();
      set({
        teams: teamPayload.teams,
        activeTeam: teamPayload.active_team,
        saving: false,
      });
    } catch (error) {
      set({ saving: false, error: error instanceof Error ? error.message : "Failed to save team version." });
    }
  },
  selectTeam: async (teamId, versionNumber) => {
    set({ saving: true, error: null });
    try {
      await api.selectStrategyTeam(teamId, versionNumber);
      const teamPayload = await api.getStrategyTeams();
      set({
        teams: teamPayload.teams,
        activeTeam: teamPayload.active_team,
        saving: false,
      });
    } catch (error) {
      set({ saving: false, error: error instanceof Error ? error.message : "Failed to select team." });
    }
  },
  updateDraftWeight: async (agent, value) => {
    const next = cloneTeam(get().compiledTeam);
    if (!next) return;
    next.agent_weights[agent] = value;
    if (next.compiled_agent_specs[agent]) {
      next.compiled_agent_specs[agent] = {
        ...next.compiled_agent_specs[agent],
        weight: value,
      };
    }
    set({ compiledTeam: next });
    try {
      const comparison = await api.compareStrategyTeam({ candidate_compiled_team: next });
      set({ comparison });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : "Failed to refresh comparison." });
    }
  },
  toggleDraftAgent: async (agent, enabled) => {
    const next = cloneTeam(get().compiledTeam);
    const defaultTeam = get().defaultTeam?.compiled_team;
    if (!next || !defaultTeam) return;
    const enabledSet = new Set(next.enabled_agents);
    if (enabled) {
      enabledSet.add(agent);
      next.agent_weights[agent] = next.agent_weights[agent] ?? defaultTeam.agent_weights[agent] ?? 50;
      next.compiled_agent_specs[agent] =
        next.compiled_agent_specs[agent] ??
        (defaultTeam.compiled_agent_specs[agent] as CompiledAgentSpec | undefined) ??
        ({
          agent_name: agent,
          enabled: true,
          weight: next.agent_weights[agent],
          prompt_pack_id: `${agent}-core`,
          prompt_pack_version: "1.0.0",
          variant_id: "balanced",
          modifiers: {},
          owned_sources: [],
          freshness_limit_minutes: 60,
          lookback_config: {},
        } satisfies CompiledAgentSpec);
    } else {
      enabledSet.delete(agent);
      delete next.compiled_agent_specs[agent];
      delete next.agent_weights[agent];
    }
    ANALYSIS_AGENTS.forEach((name) => {
      if (enabledSet.has(name) && !next.agent_weights[name]) {
        next.agent_weights[name] = defaultTeam.agent_weights[name] ?? 50;
      }
    });
    next.enabled_agents = [...enabledSet].sort();
    set({ compiledTeam: next });
    try {
      const comparison = await api.compareStrategyTeam({ candidate_compiled_team: next });
      set({ comparison });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : "Failed to refresh comparison." });
    }
  },
  updateDraftRisk: async (riskLevel) => {
    const next = cloneTeam(get().compiledTeam);
    if (!next) return;
    next.risk_level = riskLevel;
    set({ compiledTeam: next });
    try {
      const comparison = await api.compareStrategyTeam({ candidate_compiled_team: next });
      set({ comparison });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : "Failed to refresh comparison." });
    }
  },
  updateDraftHorizon: async (timeHorizon) => {
    const next = cloneTeam(get().compiledTeam);
    if (!next) return;
    next.time_horizon = timeHorizon;
    set({ compiledTeam: next });
    try {
      const comparison = await api.compareStrategyTeam({ candidate_compiled_team: next });
      set({ comparison });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : "Failed to refresh comparison." });
    }
  },
  loadPremadeCatalog: async () => {
    if (get().premadeCatalog) return;
    try {
      const catalog = await api.getPremadeTeams();
      set({ premadeCatalog: catalog });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : "Failed to load premade catalog." });
    }
  },
  applyPremadeTeam: async (teamId) => {
    set({ loading: true, error: null });
    try {
      const { compiled_team, comparison } = await api.compilePremadeTeam(teamId);
      set({ compiledTeam: cloneTeam(compiled_team), comparison, loading: false });
    } catch (error) {
      set({ loading: false, error: error instanceof Error ? error.message : "Failed to apply premade team." });
    }
  },
  clearError: () => set({ error: null }),
}));
