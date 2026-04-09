import { create } from "zustand";
import { api } from "../api/client";
import type {
  ArchitectureDraft,
  ArchitecturePatch,
  CompiledTeam,
  CustomConversation,
  NodeFamily,
  StudioMode,
  TeamEdge,
  TeamNode,
  TeamTopology,
  TeamValidationResult,
} from "../api/types";

function generateId(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

function deepCloneDraft(draft: ArchitectureDraft): ArchitectureDraft {
  return JSON.parse(JSON.stringify(draft)) as ArchitectureDraft;
}

function formatCustomTeamError(err: unknown, action: "start" | "send" | "compile"): string {
  const message = err instanceof Error ? err.message : String(err);

  if (action === "start" && /not found/i.test(message)) {
    return (
      "Custom Team builder API is unavailable. Restart the backend so the latest strategy " +
      "routes load, then try again."
    );
  }

  return message;
}

function hasConversationContent(conversation: CustomConversation | null): boolean {
  if (!conversation) {
    return false;
  }

  return Boolean(
    conversation.messages.length ||
      conversation.latest_draft ||
      conversation.latest_turn?.assistant_message?.trim(),
  );
}

interface CustomTeamState {
  conversation: CustomConversation | null;
  draft: ArchitectureDraft | null;
  compiledTeam: CompiledTeam | null;
  validationResult: TeamValidationResult | null;
  loading: boolean;
  saving: boolean;
  error: string | null;

  // Studio
  studioMode: StudioMode;
  selectedNodeId: string | null;
  pendingPatch: ArchitecturePatch | null;
  patchLoading: boolean;
  showRefinementPanel: boolean;
}

interface CustomTeamActions {
  hydrate: () => Promise<void>;
  startConversation: (seedPrompt?: string) => Promise<boolean>;
  sendMessage: (content: string, requestCompile?: boolean) => Promise<void>;
  compileDraft: () => Promise<void>;
  saveTeam: (label: string) => Promise<void>;

  // Studio
  setStudioMode: (mode: StudioMode) => void;
  selectNode: (nodeId: string | null) => void;
  setShowRefinementPanel: (show: boolean) => void;

  // Topology mutations
  updateNodeWeight: (nodeId: string, weight: number) => Promise<void>;
  updateNodeVariant: (nodeId: string, variantId: string) => Promise<void>;
  updateNodeEnabled: (nodeId: string, enabled: boolean) => Promise<void>;
  updateNodeRoleDescription: (nodeId: string, description: string) => Promise<void>;
  updateNodeDisplayName: (nodeId: string, name: string) => Promise<void>;
  updateNodeSystemPrompt: (nodeId: string, prompt: string) => Promise<void>;
  updateNodeDataDomain: (nodeId: string, domain: string) => Promise<void>;
  updateNodeParameters: (nodeId: string, parameters: Record<string, unknown>) => Promise<void>;
  updateNodeKind: (nodeId: string, kind: string) => Promise<void>;
  updateTeamName: (name: string) => Promise<void>;
  addNode: (family: NodeFamily, agentType?: string, dataDomain?: string) => Promise<void>;
  removeNode: (nodeId: string) => Promise<void>;
  addEdge: (sourceNodeId: string, targetNodeId: string) => Promise<void>;
  removeEdge: (edgeId: string) => Promise<void>;
  setNodePromptOverride: (nodeId: string, promptText: string, label: string) => Promise<void>;
  clearNodePromptOverride: (nodeId: string) => Promise<void>;
  updateNodePosition: (nodeId: string, x: number, y: number) => void;

  // LLM patch
  requestNLPatch: (instruction: string) => Promise<void>;
  confirmPatch: () => Promise<void>;
  discardPatch: () => void;

  revalidate: () => Promise<void>;
  recompile: () => Promise<void>;
  clearError: () => void;
  reset: () => void;
}

type CustomTeamStore = CustomTeamState & CustomTeamActions;

const initialState: CustomTeamState = {
  conversation: null,
  draft: null,
  compiledTeam: null,
  validationResult: null,
  loading: false,
  saving: false,
  error: null,
  studioMode: "view",
  selectedNodeId: null,
  pendingPatch: null,
  patchLoading: false,
  showRefinementPanel: false,
};

export const useCustomTeamStore = create<CustomTeamStore>((set, get) => ({
  ...initialState,

  hydrate: async () => {
    set({ loading: true, error: null });
    try {
      const { conversations } = await api.customTeam.listConversations();
      const latest = conversations.find((conversation) => hasConversationContent(conversation)) ?? null;
      if (latest) {
        set({
          conversation: latest,
          draft: latest.latest_draft,
          validationResult: latest.latest_turn?.validation_state ?? null,
          loading: false,
        });
        // Auto-recompile if topology exists but compiledTeam is absent
        if (
          latest.latest_draft?.topology?.nodes?.length &&
          !get().compiledTeam
        ) {
          await get().recompile();
        }
      } else {
        set({ loading: false });
      }
    } catch (err) {
      set({ loading: false, error: String(err) });
    }
  },

  startConversation: async (seedPrompt?: string) => {
    const normalizedPrompt = seedPrompt?.trim();
    if (!normalizedPrompt) {
      set({
        loading: false,
        error: "Describe the team you want to build before starting the custom builder.",
      });
      return false;
    }

    set({ loading: true, error: null });
    try {
      const conv = await api.customTeam.startConversation(normalizedPrompt);
      set({
        conversation: conv,
        draft: conv.latest_draft,
        compiledTeam: null,
        validationResult: conv.latest_turn?.validation_state ?? null,
        loading: false,
        studioMode: "view",
        selectedNodeId: null,
      });
      return true;
    } catch (err) {
      set({ loading: false, error: formatCustomTeamError(err, "start") });
      return false;
    }
  },

  sendMessage: async (content: string, requestCompile = true) => {
    const { conversation } = get();
    if (!conversation) return;
    set({ loading: true, error: null });
    try {
      const result = await api.customTeam.sendMessage(
        conversation.conversation_id,
        content,
        requestCompile,
      );
      const newCompiled = result.compiled_team ?? get().compiledTeam;
      // Sync draft topology from compiledTeam if available
      let newDraft = result.draft;
      if (newCompiled?.topology && newDraft) {
        newDraft = { ...newDraft, topology: newCompiled.topology };
      }
      set({
        conversation: result.conversation,
        draft: newDraft,
        compiledTeam: newCompiled,
        validationResult: result.validation_state ?? get().validationResult,
        loading: false,
      });
    } catch (err) {
      set({ loading: false, error: formatCustomTeamError(err, "send") });
    }
  },

  compileDraft: async () => {
    const { conversation } = get();
    if (!conversation) return;
    set({ loading: true, error: null });
    try {
      const result = await api.customTeam.compileConversation(conversation.conversation_id);
      set({
        conversation: result.conversation,
        draft: result.draft,
        compiledTeam: result.compiled_team,
        validationResult: result.validation_result,
        loading: false,
        studioMode: "view",
      });
    } catch (err) {
      set({ loading: false, error: formatCustomTeamError(err, "compile") });
    }
  },

  saveTeam: async (label: string) => {
    const { compiledTeam, conversation } = get();
    if (!compiledTeam) return;
    set({ saving: true, error: null });
    try {
      await api.customTeam.saveTeam({
        conversation_id: conversation?.conversation_id ?? null,
        compiled_team: compiledTeam,
        label,
      });
      set({ saving: false });
      // Refresh the shared strategy store so SavedTeamsPanel updates
      const { useStrategyStore } = await import("./strategyStore");
      await useStrategyStore.getState().hydrate();
    } catch (err) {
      set({ saving: false, error: String(err) });
    }
  },

  setStudioMode: (mode) => set({ studioMode: mode }),
  selectNode: (nodeId) => set({ selectedNodeId: nodeId, showRefinementPanel: false }),
  setShowRefinementPanel: (show) => set({ showRefinementPanel: show }),

  // ── Topology mutations ──────────────────────────────────────────────────

  _mutateDraftTopology: async (mutate: (draft: ArchitectureDraft) => void) => {
    const { draft } = get();
    if (!draft) return;
    const next = deepCloneDraft(draft);
    mutate(next);
    set({ draft: next });
    await get().revalidate();
  },

  updateNodeWeight: async (nodeId, weight) => {
    const { draft } = get();
    if (!draft) return;
    const next = deepCloneDraft(draft);
    const node = next.topology.nodes.find((n) => n.node_id === nodeId);
    if (node) node.influence_weight = Math.max(0, Math.min(100, weight));
    set({ draft: next });
    await get().recompile();
  },

  updateNodeVariant: async (nodeId, variantId) => {
    const { draft } = get();
    if (!draft) return;
    const next = deepCloneDraft(draft);
    const node = next.topology.nodes.find((n) => n.node_id === nodeId);
    if (node) node.variant_id = variantId;
    set({ draft: next });
    await get().recompile();
  },

  updateNodeEnabled: async (nodeId, enabled) => {
    const { draft } = get();
    if (!draft) return;
    const next = deepCloneDraft(draft);
    const node = next.topology.nodes.find((n) => n.node_id === nodeId);
    if (node) node.enabled = enabled;
    set({ draft: next });
    await get().recompile();
  },

  updateNodeRoleDescription: async (nodeId, description) => {
    const { draft } = get();
    if (!draft) return;
    const next = deepCloneDraft(draft);
    const node = next.topology.nodes.find((n) => n.node_id === nodeId);
    if (node) node.role_description = description;
    set({ draft: next });
    await get().recompile();
  },

  updateNodeDisplayName: async (nodeId, name) => {
    const { draft } = get();
    if (!draft) return;
    const next = deepCloneDraft(draft);
    const node = next.topology.nodes.find((n) => n.node_id === nodeId);
    if (node) node.display_name = name.slice(0, 64);
    set({ draft: next });
    await get().recompile();
  },

  updateNodeSystemPrompt: async (nodeId, prompt) => {
    const { draft } = get();
    if (!draft) return;
    const next = deepCloneDraft(draft);
    const node = next.topology.nodes.find((n) => n.node_id === nodeId);
    if (node) node.system_prompt = prompt;
    set({ draft: next });
    await get().recompile();
  },

  updateNodeDataDomain: async (nodeId, domain) => {
    const { draft } = get();
    if (!draft) return;
    const next = deepCloneDraft(draft);
    const node = next.topology.nodes.find((n) => n.node_id === nodeId);
    if (node) {
      node.data_domain = domain || null;
      node.agent_type = domain || null;
    }
    set({ draft: next });
    await get().recompile();
  },

  updateNodeParameters: async (nodeId, parameters) => {
    const { draft } = get();
    if (!draft) return;
    const next = deepCloneDraft(draft);
    const node = next.topology.nodes.find((n) => n.node_id === nodeId);
    if (node) node.parameters = { ...(node.parameters ?? {}), ...parameters };
    set({ draft: next });
    await get().recompile();
  },

  updateNodeKind: async (nodeId, kind) => {
    const { draft } = get();
    if (!draft) return;
    const next = deepCloneDraft(draft);
    const node = next.topology.nodes.find((n) => n.node_id === nodeId);
    if (node) node.node_kind = kind;
    set({ draft: next });
    await get().recompile();
  },

  updateTeamName: async (name) => {
    const trimmed = name.trim().slice(0, 64);
    if (!trimmed || trimmed.length < 3) return;
    const { draft, compiledTeam } = get();
    if (draft) {
      const next = deepCloneDraft(draft);
      next.proposed_name = trimmed;
      set({ draft: next });
    }
    if (compiledTeam) {
      set({ compiledTeam: { ...compiledTeam, name: trimmed } });
    }
    await get().recompile();
  },

  addNode: async (family, agentType, dataDomain) => {
    const { draft } = get();
    if (!draft) return;
    const next = deepCloneDraft(draft);
    const isIngestion = Boolean(dataDomain || (family === "data_ingestion" && agentType));
    const isTerminal = family === "output" || family === "terminal";
    const effectiveDomain = dataDomain ?? (isIngestion ? (agentType ?? null) : null);
    const baseLabel = effectiveDomain
      ? `${effectiveDomain.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())} Analyst`
      : isTerminal
        ? "Portfolio Decision"
        : "Custom Reasoning Node";
    const duplicateCount = next.topology.nodes.filter(
      (node) => node.display_name.startsWith(baseLabel),
    ).length;
    const newNode: TeamNode = {
      node_id: generateId(`node-${family}`),
      display_name: duplicateCount > 0 ? `${baseLabel} ${duplicateCount + 1}` : baseLabel,
      node_family: isIngestion ? "data_ingestion" : isTerminal ? "output" : "reasoning",
      agent_type: effectiveDomain ?? agentType ?? null,
      data_domain: effectiveDomain,
      system_prompt: isTerminal
        ? "You are the final decision node. Synthesize all upstream inputs and produce a final BUY/SELL/HOLD decision as JSON matching the PortfolioDecision schema."
        : "",
      node_kind: isIngestion ? "data_ingestion" : isTerminal ? "terminal" : "",
      parameters: isTerminal
        ? { output_schema: "PortfolioDecision", temperature: 0.2, max_tokens: 800, input_merge: "concatenate", is_terminal: true }
        : isIngestion
          ? {}
          : { output_schema: "ReasoningOutput", temperature: 0.3, max_tokens: 600, input_merge: "concatenate", is_terminal: false },
      role_description: "",
      enabled: true,
      visual_position: { x: 200, y: 200 },
      upstream_node_ids: [],
      downstream_node_ids: [],
      prompt_pack_id: null,
      prompt_pack_version: null,
      variant_id: "balanced",
      modifiers: {},
      prompt_override: null,
      capability_bindings: [],
      prompt_contract: null,
      mode_eligibility: {
        analyze: true,
        paper: true,
        live: true,
        backtest_strict: isIngestion,
        backtest_experimental: true,
        reasons: [],
      },
      influence_weight: 60,
      influence_group: null,
      owned_sources: [],
      freshness_limit_minutes: 120,
      lookback_config: {},
      backtest_strict_eligible: isIngestion,
      backtest_experimental_eligible: true,
      paper_eligible: true,
      live_eligible: true,
      validation_errors: [],
      validation_warnings: [],
    };
    next.topology.nodes.push(newNode);
    set({ draft: next });
    await get().recompile();
  },

  removeNode: async (nodeId) => {
    const { draft } = get();
    if (!draft) return;
    const next = deepCloneDraft(draft);
    next.topology.nodes = next.topology.nodes.filter((n) => n.node_id !== nodeId);
    next.topology.edges = next.topology.edges.filter(
      (e) => e.source_node_id !== nodeId && e.target_node_id !== nodeId,
    );
    set({ draft: next, selectedNodeId: get().selectedNodeId === nodeId ? null : get().selectedNodeId });
    await get().recompile();
  },

  addEdge: async (sourceNodeId, targetNodeId) => {
    const { draft } = get();
    if (!draft) return;
    // Prevent duplicate edges
    const exists = draft.topology.edges.some(
      (e) => e.source_node_id === sourceNodeId && e.target_node_id === targetNodeId,
    );
    if (exists) return;
    const next = deepCloneDraft(draft);
    const newEdge: TeamEdge = {
      edge_id: generateId("edge"),
      source_node_id: sourceNodeId,
      target_node_id: targetNodeId,
      label: "",
      edge_type: "signal",
    };
    next.topology.edges.push(newEdge);
    set({ draft: next });
    await get().recompile();
  },

  removeEdge: async (edgeId) => {
    const { draft } = get();
    if (!draft) return;
    const next = deepCloneDraft(draft);
    next.topology.edges = next.topology.edges.filter((e) => e.edge_id !== edgeId);
    set({ draft: next });
    await get().recompile();
  },

  setNodePromptOverride: async (nodeId, promptText, label) => {
    const { draft } = get();
    if (!draft) return;
    const next = deepCloneDraft(draft);
    const node = next.topology.nodes.find((n) => n.node_id === nodeId);
    if (node) {
      node.prompt_override = {
        override_id: generateId("override"),
        node_id: nodeId,
        label,
        system_prompt_text: promptText,
        created_at: new Date().toISOString(),
        warning:
          "Prompt overrides disable strict backtest eligibility and mark the team as experimental_custom.",
      };
    }
    set({ draft: next });
    await get().recompile();
  },

  clearNodePromptOverride: async (nodeId) => {
    const { draft } = get();
    if (!draft) return;
    const next = deepCloneDraft(draft);
    const node = next.topology.nodes.find((n) => n.node_id === nodeId);
    if (node) node.prompt_override = null;
    set({ draft: next });
    await get().recompile();
  },

  updateNodePosition: (nodeId, x, y) => {
    const { draft } = get();
    if (!draft) return;
    const next = deepCloneDraft(draft);
    const node = next.topology.nodes.find((n) => n.node_id === nodeId);
    if (node) node.visual_position = { x, y };
    set({ draft: next });
    // No revalidation needed for position changes
  },

  // ── LLM patch ────────────────────────────────────────────────────────────

  requestNLPatch: async (instruction) => {
    const { compiledTeam } = get();
    if (!compiledTeam) return;
    set({ patchLoading: true, error: null });
    try {
      const patch = await api.customTeam.generatePatch(
        compiledTeam.team_id,
        instruction,
        compiledTeam.version_number,
        compiledTeam,
      );
      set({ pendingPatch: patch, patchLoading: false });
    } catch (err) {
      set({ patchLoading: false, error: String(err) });
    }
  },

  confirmPatch: async () => {
    const { pendingPatch, compiledTeam } = get();
    if (!pendingPatch || !compiledTeam) return;
    set({ patchLoading: true, error: null });
    try {
      const result = await api.customTeam.applyPatch(
        pendingPatch,
        compiledTeam.team_id,
        `Patch: ${pendingPatch.patch_description.slice(0, 60)}`,
        compiledTeam.version_number,
        compiledTeam,
      );
      set({
        compiledTeam: result.compiled_team,
        validationResult: result.validation_result,
        pendingPatch: null,
        patchLoading: false,
      });
      // Sync draft topology from compiled team if topology exists
      if (result.compiled_team.topology) {
        const { draft } = get();
        if (draft) {
          const next = deepCloneDraft(draft);
          next.topology = result.compiled_team.topology;
          set({ draft: next });
        }
      }
    } catch (err) {
      set({ patchLoading: false, error: String(err) });
    }
  },

  discardPatch: () => set({ pendingPatch: null }),

  revalidate: async () => {
    const { draft } = get();
    if (!draft) return;
    try {
      const result = await api.customTeam.validateTopology(
        draft.topology,
        draft.intent,
      );
      set({ validationResult: result });
    } catch {
      // Non-fatal — don't surface validation API errors
    }
  },

  recompile: async () => {
    const { draft } = get();
    if (!draft) return;
    set({ loading: true, error: null });
    try {
      const result = await api.customTeam.compileTopology(
        draft.topology,
        draft.intent,
        draft.proposed_name,
        draft.proposed_description,
      );
      // Sync compiledTeam.topology back to draft so visual stays current
      let syncedDraft = draft;
      if (result.compiled_team.topology) {
        syncedDraft = { ...draft, topology: result.compiled_team.topology };
      }
      set({
        compiledTeam: result.compiled_team,
        validationResult: result.validation_result,
        draft: syncedDraft,
        loading: false,
      });
    } catch (err) {
      set({ loading: false, error: String(err) });
    }
  },

  clearError: () => set({ error: null }),
  reset: () => set(initialState),
}));
