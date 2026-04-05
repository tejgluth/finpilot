interface AgentWeightSliderProps {
  agent: string;
  value: number;
  onChange?: (value: number) => void;
  disabled?: boolean;
}

export default function AgentWeightSlider({ agent, value, onChange, disabled }: AgentWeightSliderProps) {
  return (
    <div className={`rounded-2xl px-4 py-3 ${disabled ? "bg-slate/60 text-ink/45" : "bg-slate"}`}>
      <div className="mb-2 flex items-center justify-between">
        <span className="font-semibold capitalize">{agent}</span>
        <span className="font-mono text-xs text-ink/55">{value}%</span>
      </div>
      <input
        className="w-full accent-tide"
        disabled={disabled}
        max={100}
        min={0}
        onChange={(event) => onChange?.(Number(event.target.value))}
        type="range"
        value={value}
      />
    </div>
  );
}
