import type { TradingStatusPayload } from "../../api/types";
import Panel from "../common/Panel";

export default function LiveTradingNotice({ status }: { status: TradingStatusPayload }) {
  const isLive = status.alpaca_mode === "live";

  return (
    <Panel title="Live trading responsibility" eyebrow="Mode awareness">
      <div className="space-y-3 text-sm leading-6 text-ink/75">
        <p>
          FinPilot does not unlock or approve live trading for you. If you switch Alpaca to
          <code> live </code>
          mode, that is your decision and your real account is on the line.
        </p>
        <div className={`rounded-2xl px-4 py-3 ${isLive ? "bg-ember/10 text-ember" : "bg-slate text-ink/75"}`}>
          {isLive
            ? "Live mode is active. Real money is at risk, and every order remains your responsibility."
            : "Paper mode is active. You can stay in simulation as long as you want, or move to live only when you decide to do it."}
        </div>
        <ul className="grid gap-2">
          <li className="rounded-2xl bg-slate px-4 py-3">
            Guardrails and the kill switch are safety tools, not permission from the app to trade live.
          </li>
          <li className="rounded-2xl bg-slate px-4 py-3">
            Switching modes is up to you in setup or your local environment.
          </li>
          <li className="rounded-2xl bg-slate px-4 py-3">
            Full Manual, Semi-Auto, and Full Auto only change confirmation behavior.
          </li>
        </ul>
      </div>
    </Panel>
  );
}
