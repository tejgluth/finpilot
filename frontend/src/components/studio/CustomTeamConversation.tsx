import { useDeferredValue, useEffect, useRef, useState } from "react";
import clsx from "clsx";
import { useCustomTeamStore } from "../../stores/customTeamStore";
import ThinkingDots from "../common/ThinkingDots";

const SEED_SUGGESTIONS = [
  "Technical-focused short-term team with momentum secondary",
  "Macro-driven conservative team, avoid growth stocks",
  "Balanced fundamentals + sentiment team for mid-cap equity",
];

export default function CustomTeamConversation() {
  const {
    conversation,
    draft,
    loading,
    error,
    startConversation,
    sendMessage,
    compileDraft,
    clearError,
  } = useCustomTeamStore();

  const [input, setInput] = useState("");
  const [seedPrompt, setSeedPrompt] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messages = useDeferredValue(conversation?.messages ?? []);
  const latestTurn = conversation?.latest_turn;
  const modeBadges = latestTurn
    ? [
        { label: "Analyze", supported: latestTurn.mode_compatibility.analyze },
        { label: "Paper", supported: latestTurn.mode_compatibility.paper },
        { label: "Live", supported: latestTurn.mode_compatibility.live },
        { label: "Strict BT", supported: latestTurn.mode_compatibility.backtest_strict },
        {
          label: "Exp BT",
          supported: latestTurn.mode_compatibility.backtest_experimental,
        },
      ]
    : [];

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleStart(e: React.FormEvent) {
    e.preventDefault();
    const prompt = seedPrompt.trim() || undefined;
    const started = await startConversation(prompt);
    if (started) {
      setSeedPrompt("");
    }
  }

  function handleSend(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;
    void sendMessage(text, true);
    setInput("");
  }

  const followUpQuestion = latestTurn?.open_questions?.[0]?.question ?? draft?.follow_up_question;
  const hasTopology = draft?.topology?.nodes && draft.topology.nodes.length > 0;

  // No conversation yet — show seed prompt form
  if (!conversation) {
    return (
      <div className="space-y-6">
        <div className="rounded-[28px] border border-white/70 bg-white/80 p-8 shadow-soft backdrop-blur-sm">
          <p className="mb-1 font-mono text-[10px] uppercase tracking-widest text-ink/40">
            Custom Team Builder
          </p>
          <h2 className="mb-2 font-display text-xl font-semibold text-ink">
            Design your own agent team
          </h2>
          <p className="mb-6 text-sm leading-relaxed text-ink/60">
            Describe the team you want to build — which analysis signals to include, your risk
            tolerance, time horizon, and any sectors to avoid. The builder will ask follow-up
            questions until the topology is clear.
          </p>

          {error && (
            <div className="mb-4 flex items-start justify-between gap-3 rounded-xl bg-ember/10 px-4 py-3">
              <p className="text-sm text-ember">{error}</p>
              <button
                className="text-[12px] text-ember/70 hover:text-ember"
                onClick={clearError}
                type="button"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* Seed suggestions */}
          <div className="mb-4 flex flex-wrap gap-2">
            {SEED_SUGGESTIONS.map((s) => (
              <button
                key={s}
                className="rounded-full border border-tide/30 bg-tide/5 px-3 py-1.5 text-[12px] text-tide hover:bg-tide/10"
                onClick={() => setSeedPrompt(s)}
                type="button"
              >
                {s}
              </button>
            ))}
          </div>

          <form className="space-y-3" onSubmit={handleStart}>
            <textarea
              className="w-full min-h-28 resize-none rounded-[20px] border border-ink/10 bg-slate/50 px-4 py-3 text-sm text-ink focus:border-tide focus:outline-none focus:ring-2 focus:ring-tide/20"
              onChange={(e) => setSeedPrompt(e.target.value)}
              placeholder="Describe the team you want to build…"
              value={seedPrompt}
            />
            <div className="flex justify-end">
              <button
                className="rounded-full bg-tide px-6 py-2.5 text-sm font-semibold text-white hover:bg-tide/90 disabled:opacity-40"
                disabled={loading}
                type="submit"
              >
                {loading ? <ThinkingDots className="text-white" /> : "Start building"}
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-[28px] border border-white/70 bg-white/80 shadow-soft backdrop-blur-sm overflow-hidden">
        {/* Chat messages */}
        <div className="max-h-[420px] overflow-y-auto p-4">
          <div className="space-y-3">
            {messages.length === 0 && (
              <p className="text-sm text-ink/40 text-center py-4">
                Starting conversation <ThinkingDots className="text-ink/40" />
              </p>
            )}
            {messages.map((msg) => (
              <div
                key={msg.message_id}
                className={clsx(
                  "max-w-[88%] rounded-[20px] px-4 py-3",
                  msg.role === "user"
                    ? "ml-auto bg-tide text-white"
                    : "bg-slate/80 text-ink shadow-soft",
                )}
              >
                <p className="text-[10px] font-mono uppercase tracking-widest opacity-60 mb-1">
                  {msg.role}
                </p>
                <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
              </div>
            ))}
            {loading && (
              <div className="max-w-[88%] rounded-[20px] bg-slate/80 px-4 py-3 text-ink shadow-soft">
                <ThinkingDots />
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Follow-up question callout */}
        {followUpQuestion && !loading && (
          <div className="mx-4 mb-3 rounded-xl border border-tide/30 bg-tide/5 px-4 py-3">
            <p className="text-[11px] font-mono uppercase tracking-wide text-tide/70 mb-1">
              Follow-up
            </p>
            <p className="text-sm text-ink">{followUpQuestion}</p>
          </div>
        )}

        {/* Input form */}
        <div className="border-t border-ink/8 p-4">
          <form className="flex gap-3" onSubmit={handleSend}>
            <textarea
              className="flex-1 min-h-[48px] max-h-32 resize-none rounded-[16px] border border-ink/10 bg-slate/50 px-3 py-2.5 text-sm text-ink focus:border-tide focus:outline-none focus:ring-2 focus:ring-tide/20"
              disabled={loading}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend(e as unknown as React.FormEvent);
                }
              }}
              placeholder="Reply to the assistant…"
              rows={1}
              value={input}
            />
            <button
              className="self-end rounded-full bg-tide px-5 py-2.5 text-sm font-semibold text-white hover:bg-tide/90 disabled:opacity-40"
              disabled={loading || !input.trim()}
              type="submit"
            >
              {loading ? <ThinkingDots className="text-white" /> : "Send"}
            </button>
          </form>
        </div>
      </div>

      {/* Action row */}
      {hasTopology && (
        <div className="flex items-center justify-between gap-4 rounded-[20px] border border-ink/8 bg-white px-5 py-4">
          <div>
            <p className="text-sm font-medium text-ink">
              Topology ready — {draft!.topology.nodes.length} nodes
            </p>
            <p className="text-[12px] text-ink/50">
              {draft?.proposed_name ?? "Custom Team"}
            </p>
          </div>
          <button
            className="rounded-full bg-ink px-6 py-2.5 text-sm font-semibold text-white hover:bg-ink/80 disabled:opacity-40"
            disabled={loading}
            onClick={() => void compileDraft()}
            type="button"
          >
            {loading ? <ThinkingDots className="text-white" /> : "Compile team →"}
          </button>
        </div>
      )}

      {latestTurn && (
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="rounded-[20px] border border-ink/8 bg-white px-5 py-4">
            <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-ink/35">
              Resolved
            </p>
            <div className="space-y-2">
              {latestTurn.resolved_requirements.length > 0 ? (
                latestTurn.resolved_requirements.map((item) => (
                  <div key={item.requirement_id} className="rounded-xl bg-emerald-50 px-3 py-2">
                    <p className="text-[11px] font-medium text-emerald-800">{item.label}</p>
                    <p className="text-[12px] text-emerald-700">{item.value}</p>
                  </div>
                ))
              ) : (
                <p className="text-[12px] text-ink/45">The architect is still gathering the core design requirements.</p>
              )}
            </div>
          </div>

          <div className="rounded-[20px] border border-ink/8 bg-white px-5 py-4">
            <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-ink/35">
              Graph Changes
            </p>
            <div className="space-y-2">
              {latestTurn.graph_change_summary.length > 0 ? (
                latestTurn.graph_change_summary.map((item, index) => (
                  <p key={index} className="rounded-xl bg-slate/60 px-3 py-2 text-[12px] text-ink/75">
                    {item}
                  </p>
                ))
              ) : (
                <p className="text-[12px] text-ink/45">No graph diff yet.</p>
              )}
            </div>
          </div>

          <div className="rounded-[20px] border border-ink/8 bg-white px-5 py-4">
            <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-ink/35">
              Mode Support
            </p>
            <div className="grid grid-cols-2 gap-2">
              {modeBadges.map(({ label, supported }) => (
                <div
                  key={label}
                  className={clsx(
                    "rounded-xl border px-2 py-1.5 text-center text-[11px] font-medium",
                    supported
                      ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                      : "border-ember/20 bg-ember/5 text-ember",
                  )}
                >
                  {label}
                </div>
              ))}
            </div>
            {latestTurn.mode_compatibility.reasons.length > 0 && (
              <div className="mt-3 space-y-1">
                {latestTurn.mode_compatibility.reasons.slice(0, 4).map((reason, index) => (
                  <p key={index} className="text-[11px] text-ink/55">
                    • {reason}
                  </p>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {latestTurn && latestTurn.capability_gaps.length > 0 && (
        <div className="rounded-[20px] border border-gold/30 bg-gold/5 px-5 py-4">
          <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-gold">
            Capability Gaps
          </p>
          <div className="space-y-2">
            {latestTurn.capability_gaps.map((gap) => (
              <div key={gap.capability_id} className="rounded-xl bg-white/70 px-3 py-2">
                <p className="text-[12px] font-medium text-ink">{gap.label}</p>
                <p className="text-[12px] text-ink/65">{gap.detail}</p>
                {gap.recommended_action && (
                  <p className="mt-1 text-[11px] text-ink/45">{gap.recommended_action}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {error && (
        <div className="flex items-start justify-between gap-3 rounded-xl bg-ember/10 px-4 py-3">
          <p className="text-sm text-ember">{error}</p>
          <button
            className="text-[12px] text-ember/70 hover:text-ember"
            onClick={clearError}
            type="button"
          >
            Dismiss
          </button>
        </div>
      )}
    </div>
  );
}
