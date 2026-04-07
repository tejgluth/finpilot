import clsx from "clsx";

const DATA_INGESTION_ENTRIES = [
  { domain: "fundamentals", label: "Fundamentals", description: "Earnings, balance sheet, cash flow" },
  { domain: "technicals", label: "Technicals", description: "Price action, RSI, MACD, MAs" },
  { domain: "sentiment", label: "Sentiment", description: "News, social media, options flow" },
  { domain: "macro", label: "Macro", description: "Rates, inflation, yield curve" },
  { domain: "value", label: "Value", description: "P/E, P/B, free cash flow yield" },
  { domain: "momentum", label: "Momentum", description: "Relative strength, return rankings" },
  { domain: "growth", label: "Growth", description: "Revenue and earnings acceleration" },
] as const;

interface Props {
  onAdd: (family: string, agentType?: string, dataDomain?: string) => void;
  hasTerminalNode?: boolean;
}

export default function NodePalette({ onAdd, hasTerminalNode = false }: Props) {
  return (
    <div className="flex h-full flex-col gap-4">
      {/* Data Ingestion */}
      <div>
        <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-ink/40">
          Data Ingestion
        </p>
        <div className="space-y-1">
          {DATA_INGESTION_ENTRIES.map((entry) => (
            <button
              key={entry.domain}
              className="w-full rounded-xl border border-l-4 border-l-tide bg-tide/5 px-3 py-2 text-left transition-colors hover:bg-tide/10"
              onClick={() => onAdd("data_ingestion", entry.domain, entry.domain)}
              type="button"
            >
              <p className="text-[12px] font-semibold text-ink">{entry.label}</p>
              <p className="text-[10px] text-ink/50">{entry.description}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Reasoning Node */}
      <div>
        <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-ink/40">
          Reasoning
        </p>
        <button
          className="w-full rounded-xl border border-l-4 border-l-amber-400 bg-amber-50 px-3 py-2.5 text-left transition-colors hover:bg-amber-100"
          onClick={() => onAdd("reasoning")}
          type="button"
        >
          <p className="text-[12px] font-semibold text-ink">Custom Reasoning Node</p>
          <p className="text-[10px] text-ink/50">
            Blank node — you define its system prompt and behavior
          </p>
        </button>
      </div>

      {/* Output Node */}
      <div>
        <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-ink/40">
          Output
        </p>
        <button
          className={clsx(
            "w-full rounded-xl border border-l-4 border-l-emerald-500 bg-emerald-50 px-3 py-2.5 text-left transition-colors",
            hasTerminalNode
              ? "cursor-not-allowed opacity-40"
              : "hover:bg-emerald-100",
          )}
          disabled={hasTerminalNode}
          onClick={() => onAdd("output")}
          title={hasTerminalNode ? "A terminal output node already exists" : undefined}
          type="button"
        >
          <p className="text-[12px] font-semibold text-ink">Output Node</p>
          <p className="text-[10px] text-ink/50">
            Terminal node — produces the final portfolio decision
            {hasTerminalNode && " (already present)"}
          </p>
        </button>
      </div>
    </div>
  );
}
