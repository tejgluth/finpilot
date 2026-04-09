import { NavLink } from "react-router-dom";

type NavItem = { to: string; label: string; icon: React.ReactNode };

function Icon({ children, title }: { children: React.ReactNode; title: string }) {
  return (
    <svg
      aria-hidden="true"
      fill="none"
      height="15"
      role="img"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.75"
      viewBox="0 0 24 24"
      width="15"
    >
      <title>{title}</title>
      {children}
    </svg>
  );
}

const NAV_ITEMS: NavItem[] = [
  {
    to: "/",
    label: "Setup",
    icon: (
      <Icon title="Setup">
        <circle cx="12" cy="12" r="3" />
        <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
      </Icon>
    ),
  },
  {
    to: "/strategy",
    label: "Strategy",
    icon: (
      <Icon title="Strategy">
        <rect height="5" rx="2" width="20" x="2" y="3" />
        <rect height="5" rx="2" width="20" x="2" y="10" />
        <rect height="5" rx="2" width="20" x="2" y="17" />
      </Icon>
    ),
  },
  {
    to: "/backtest",
    label: "Backtest",
    icon: (
      <Icon title="Backtest">
        <line x1="18" x2="18" y1="20" y2="10" />
        <line x1="12" x2="12" y1="20" y2="4" />
        <line x1="6" x2="6" y1="20" y2="14" />
      </Icon>
    ),
  },
  {
    to: "/portfolio",
    label: "Portfolio",
    icon: (
      <Icon title="Portfolio">
        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
        <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
        <line x1="12" x2="12" y1="22.08" y2="12" />
      </Icon>
    ),
  },
  {
    to: "/trading",
    label: "Trading",
    icon: (
      <Icon title="Trading">
        <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
      </Icon>
    ),
  },
  {
    to: "/audit",
    label: "Audit",
    icon: (
      <Icon title="Audit">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" x2="8" y1="13" y2="13" />
        <line x1="16" x2="8" y1="17" y2="17" />
        <polyline points="10 9 9 9 8 9" />
      </Icon>
    ),
  },
  {
    to: "/settings",
    label: "Settings",
    icon: (
      <Icon title="Settings">
        <line x1="4" x2="4" y1="21" y2="14" />
        <line x1="4" x2="4" y1="10" y2="3" />
        <line x1="12" x2="12" y1="21" y2="12" />
        <line x1="12" x2="12" y1="8" y2="3" />
        <line x1="20" x2="20" y1="21" y2="16" />
        <line x1="20" x2="20" y1="12" y2="3" />
        <line x1="1" x2="7" y1="14" y2="14" />
        <line x1="9" x2="15" y1="8" y2="8" />
        <line x1="17" x2="23" y1="16" y2="16" />
      </Icon>
    ),
  },
];

export default function Sidebar() {
  return (
    <aside className="flex h-full flex-col rounded-[32px] border border-white/70 bg-white/70 p-5 shadow-soft backdrop-blur-sm">
      {/* Brand */}
      <div className="mb-7">
        <div className="mb-1 flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-tide/10">
            <svg
              fill="none"
              height="14"
              stroke="#2f6f6d"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              viewBox="0 0 24 24"
              width="14"
            >
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
          </div>
          <span className="font-mono text-[11px] font-semibold uppercase tracking-[0.3em] text-tide">FinPilot</span>
        </div>
        <div className="font-display text-2xl leading-snug text-ink">
          Local investing lab
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-0.5">
        {NAV_ITEMS.map(({ to, label, icon }) => (
          <NavLink
            end={to === "/"}
            key={to}
            to={to}
            className={({ isActive }) =>
              [
                "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-all duration-150",
                isActive
                  ? "bg-ink text-white shadow-sm"
                  : "text-ink/60 hover:bg-ink/5 hover:text-ink",
              ].join(" ")
            }
          >
            {icon}
            <span className="font-medium">{label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Footer mode indicator */}
      <div className="mt-4 rounded-xl bg-pine/8 px-3 py-2.5">
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-pine" />
          <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.25em] text-pine">Paper mode</span>
        </div>
        <p className="mt-0.5 text-[11px] text-ink/50">No live trades are placed</p>
      </div>
    </aside>
  );
}
