export default function PositionRow({
  ticker,
  quantity,
  marketValue,
  unrealizedPnl,
}: {
  ticker: string;
  quantity: number;
  marketValue: number;
  unrealizedPnl: number;
}) {
  return (
    <div className="grid grid-cols-4 gap-3 rounded-2xl bg-slate px-4 py-3 text-sm">
      <div className="font-semibold">{ticker}</div>
      <div>{quantity}</div>
      <div>${marketValue.toFixed(2)}</div>
      <div className={unrealizedPnl >= 0 ? "text-pine" : "text-ember"}>${unrealizedPnl.toFixed(2)}</div>
    </div>
  );
}
