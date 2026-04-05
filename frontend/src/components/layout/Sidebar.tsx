import { NavLink } from "react-router-dom";

const links = [
  ["/", "Setup"],
  ["/strategy", "Strategy"],
  ["/backtest", "Backtest"],
  ["/portfolio", "Portfolio"],
  ["/trading", "Trading"],
  ["/audit", "Audit"],
  ["/settings", "Settings"],
];

export default function Sidebar() {
  return (
    <aside className="rounded-[32px] border border-white/70 bg-white/70 p-5 shadow-soft backdrop-blur-sm">
      <div className="mb-8">
        <div className="font-mono text-[11px] uppercase tracking-[0.35em] text-tide/70">FinPilot</div>
        <div className="mt-2 font-display text-3xl leading-none text-ink">Local-first investing lab</div>
      </div>
      <nav className="space-y-2">
        {links.map(([to, label]) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              [
                "block rounded-2xl px-4 py-3 text-sm transition",
                isActive ? "bg-ink text-white" : "text-ink/70 hover:bg-ink/5 hover:text-ink",
              ].join(" ")
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
