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
        <div className="max-h-[420px] overflow-y-auto rounded-[24px] bg-slate/60 p-4">
          <div className="space-y-3">
            {deferredMessages.length ? (
              <>
                {deferredMessages.map((message) => (
                  <div
                    className={[
                      "max-w-[90%] rounded-[20px] px-4 py-3 text-sm",
                      message.role === "user"
                        ? "ml-auto bg-tide text-white"
                        : "bg-white text-ink shadow-sm",
                    ].join(" ")}
                    key={message.message_id}
                  >
                    <div className="mb-1 font-mono text-[9px] uppercase tracking-[0.25em] opacity-50">
                      {message.role === "user" ? "You" : "Builder"}
                      {" / "}
                      {message.message_type}
                    </div>
                    <div>{message.content}</div>
                  </div>
                ))}
                {loading && (
                  <div className="max-w-[90%] rounded-[20px] bg-white px-4 py-3 text-ink shadow-sm">
                    <ThinkingDots />
                  </div>
                )}
              </>
            ) : (
              <p className="text-sm leading-relaxed text-ink/55">
                Describe the team you want. For example: short-term semiconductor
                breakout team with momentum secondary, avoid financials.
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
            className="min-h-28 w-full rounded-[20px] border border-ink/10 bg-white px-4 py-3 text-sm outline-none transition focus:border-tide/60 focus:ring-2 focus:ring-tide/10"
            onChange={(event) => setPrompt(event.target.value)}
            placeholder="Describe your team — signals to emphasize, sectors to avoid, risk tolerance, and time horizon."
            value={prompt}
          />
          <div className="flex items-center justify-between gap-3">
            <div className="text-[11px] leading-relaxed text-ink/45">
              Conversation is saved locally. Only agents from the trusted catalog are used.
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

        {error ? (
          <div className="rounded-2xl bg-ember/10 px-4 py-3 text-sm text-ember">
            {error}
          </div>
        ) : null}
      </div>
    </Panel>
  );
}
