export default function ThinkingDots({ className = "" }: { className?: string }) {
  return (
    <span aria-label="Thinking" className={`inline-flex items-center gap-[3px] ${className}`} role="status">
      <span className="thinking-dot" />
      <span className="thinking-dot" />
      <span className="thinking-dot" />
    </span>
  );
}
