import { startTransition, useDeferredValue, useState } from "react";
import type { StrategyConversation } from "../../api/types";
import Panel from "../common/Panel";
import ThinkingDots from "../common/ThinkingDots";

export default function StrategyChat({
  conversation,
  onSubmit,
  onCompile,
  loading,
  error,
}: {
  conversation: StrategyConversation | null;
  onSubmit: (prompt: string) => void;
  onCompile: () => void;
  loading: boolean;
  error: string | null;
}) {
  const [prompt, setPrompt] = useState("");
  const deferredMessages = useDeferredValue(conversation?.messages ?? []);

  return (
    <Panel
      title="Conversational team builder"
      eyebrow="Strategy"
      action={
        <button
          className="rounded-full border border-ink/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-ink/70"
          onClick={() => startTransition(() => onCompile())}
          type="button"
        >
          Compile
        </button>
      }
    >
      <div className="space-y-3">
        <div className="max-h-[420px] overflow-y-auto rounded-[24px] bg-slate/70 p-4">
          <div className="space-y-3">
            {deferredMessages.length ? (
              <>
                {deferredMessages.map((message) => (
                  <div
                    className={`max-w-[90%] rounded-[22px] px-4 py-3 text-sm ${
                      message.role === "user"
                        ? "ml-auto bg-tide text-white"
                        : "bg-white text-ink shadow-soft"
                    }`}
                    key={message.message_id}
                  >
                    <div className="mb-1 text-[10px] font-mono uppercase tracking-[0.3em] opacity-70">
                      {message.role} / {message.message_type}
                    </div>
                    <div>{message.content}</div>
                  </div>
                ))}
                {loading && (
                  <div className="max-w-[90%] rounded-[22px] bg-white px-4 py-3 text-ink shadow-soft">
                    <ThinkingDots />
                  </div>
                )}
              </>
            ) : (
              <p className="text-sm text-ink/60">
                Start with a concrete request such as “Build a short-term semiconductor breakout team with sentiment
                secondary and avoid financials.”
              </p>
            )}
          </div>
        </div>

        <form
          className="space-y-3"
          onSubmit={(event) => {
            event.preventDefault();
            const nextPrompt = prompt.trim();
            if (!nextPrompt) return;
            startTransition(() => onSubmit(nextPrompt));
            setPrompt("");
          }}
        >
          <textarea
            className="min-h-32 w-full rounded-[22px] border border-ink/10 bg-white px-4 py-3 text-base outline-none transition focus:border-tide"
            onChange={(event) => setPrompt(event.target.value)}
            placeholder="Describe the team you want, what to emphasize, what to avoid, and any investor styles to imitate."
            value={prompt}
          />
          <div className="flex items-center justify-between gap-3">
            <div className="text-xs text-ink/55">
              Multi-turn state is persisted locally. The builder only uses the trusted executable catalog.
            </div>
            <button
              className="rounded-full bg-tide px-5 py-3 text-sm font-semibold text-white"
              disabled={loading}
              type="submit"
            >
              {loading ? <ThinkingDots className="text-white" /> : "Send"}
            </button>
          </div>
        </form>

        {error ? <div className="rounded-2xl bg-ember/10 px-4 py-3 text-sm text-ember">{error}</div> : null}
      </div>
    </Panel>
  );
}
