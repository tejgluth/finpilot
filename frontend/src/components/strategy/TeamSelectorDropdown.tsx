import clsx from "clsx";
import { useEffect, useMemo, useRef, useState } from "react";
import type { TeamVersion } from "../../api/types";

export interface TeamSelectorExtraOption {
  key: string;
  label: string;
  subtitle?: string;
  active?: boolean;
  onSelect: () => void | Promise<void>;
}

export interface TeamSelectorDropdownProps {
  teams: TeamVersion[];
  activeTeam: TeamVersion | null;
  onSelectTeam: (teamId: string, versionNumber: number) => void | Promise<void>;
  currentLabel?: string;
  currentSubtitle?: string;
  extraOptions?: TeamSelectorExtraOption[];
  disabled?: boolean;
  align?: "left" | "right";
  className?: string;
  buttonClassName?: string;
  labelClassName?: string;
  subtitleClassName?: string;
  menuClassName?: string;
  searchPlaceholder?: string;
}

interface DropdownOption {
  key: string;
  label: string;
  subtitle?: string;
  active: boolean;
  matchText: string;
  onSelect: () => void | Promise<void>;
}

function teamKey(team: TeamVersion): string {
  return `${team.team_id}:${team.version_number}`;
}

export default function TeamSelectorDropdown({
  teams,
  activeTeam,
  onSelectTeam,
  currentLabel,
  currentSubtitle,
  extraOptions = [],
  disabled = false,
  align = "left",
  className,
  buttonClassName,
  labelClassName,
  subtitleClassName,
  menuClassName,
  searchPlaceholder = "Search teams...",
}: TeamSelectorDropdownProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  const resolvedLabel = currentLabel ?? activeTeam?.compiled_team.name ?? "Select a team";
  const resolvedSubtitle =
    currentSubtitle ?? (activeTeam ? `v${activeTeam.version_number} · active team` : undefined);

  useEffect(() => {
    if (!open) {
      setQuery("");
      return;
    }

    searchRef.current?.focus();

    function handlePointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [open]);

  const options = useMemo<DropdownOption[]>(() => {
    const extra: DropdownOption[] = extraOptions.map((option) => ({
      key: option.key,
      label: option.label,
      subtitle: option.subtitle,
      active: option.active ?? false,
      matchText: `${option.label} ${option.subtitle ?? ""}`.toLowerCase(),
      onSelect: option.onSelect,
    }));

    const teamOptions: DropdownOption[] = teams.map((team) => ({
      key: teamKey(team),
      label: team.compiled_team.name,
      subtitle: `v${team.version_number} · ${team.label}`,
      active:
        team.team_id === activeTeam?.team_id &&
        team.version_number === activeTeam?.version_number,
      matchText: [
        team.compiled_team.name,
        team.label,
        team.team_id,
        team.version_number,
        team.compiled_team.description,
      ]
        .join(" ")
        .toLowerCase(),
      onSelect: () => onSelectTeam(team.team_id, team.version_number),
    }));

    return [...extra, ...teamOptions];
  }, [activeTeam, extraOptions, onSelectTeam, teams]);

  const filteredOptions = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    const visible = normalized
      ? options.filter((option) => option.matchText.includes(normalized))
      : options;

    return [...visible].sort((left, right) => {
      if (left.active !== right.active) {
        return left.active ? -1 : 1;
      }
      return left.label.localeCompare(right.label);
    });
  }, [options, query]);

  async function handleSelect(option: DropdownOption) {
    await option.onSelect();
    setOpen(false);
  }

  return (
    <div className={clsx("relative", className)} ref={rootRef}>
      <button
        className={clsx(
          "group flex min-w-0 items-center gap-2 text-left transition-colors",
          disabled ? "cursor-not-allowed opacity-60" : "hover:text-tide",
          buttonClassName,
        )}
        disabled={disabled}
        onClick={() => setOpen((current) => !current)}
        type="button"
      >
        <div className="min-w-0">
          <div
            className={clsx(
              "truncate font-display text-lg font-semibold text-ink transition-colors group-hover:text-tide",
              labelClassName,
            )}
          >
            {resolvedLabel}
          </div>
          {resolvedSubtitle ? (
            <div
              className={clsx(
                "truncate text-[12px] text-ink/45",
                subtitleClassName,
              )}
            >
              {resolvedSubtitle}
            </div>
          ) : null}
        </div>
        <span className="shrink-0 text-sm text-ink/45 transition-transform group-hover:text-tide">
          {open ? "▴" : "▾"}
        </span>
      </button>

      {open ? (
        <div
          className={clsx(
            "absolute z-30 mt-3 w-[min(24rem,calc(100vw-2rem))] rounded-[22px] border border-ink/10 bg-white/95 p-3 shadow-soft backdrop-blur-sm",
            align === "right" ? "right-0" : "left-0",
            menuClassName,
          )}
        >
          <input
            ref={searchRef}
            className="w-full rounded-2xl border border-ink/10 bg-slate/70 px-3 py-2 text-sm text-ink outline-none transition focus:border-tide focus:ring-2 focus:ring-tide/20"
            onChange={(event) => setQuery(event.target.value)}
            placeholder={searchPlaceholder}
            type="text"
            value={query}
          />

          <div className="mt-3 max-h-72 space-y-1 overflow-y-auto">
            {filteredOptions.length ? (
              filteredOptions.map((option) => (
                <button
                  className={clsx(
                    "flex w-full items-start justify-between gap-3 rounded-2xl px-3 py-2.5 text-left transition",
                    option.active
                      ? "bg-tide/10 text-tide"
                      : "text-ink hover:bg-slate",
                  )}
                  key={option.key}
                  onClick={() => void handleSelect(option)}
                  type="button"
                >
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold">{option.label}</div>
                    {option.subtitle ? (
                      <div className="truncate text-[12px] text-ink/50">
                        {option.subtitle}
                      </div>
                    ) : null}
                  </div>
                  {option.active ? (
                    <span className="shrink-0 rounded-full bg-white/80 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-tide">
                      Active
                    </span>
                  ) : null}
                </button>
              ))
            ) : (
              <div className="rounded-2xl bg-slate px-3 py-4 text-sm text-ink/50">
                No teams match "{query}".
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
