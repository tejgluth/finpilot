import { useState, useRef, useEffect } from "react";

const NAME_REGEX = /^[A-Za-z0-9 _-]+$/;

interface Props {
  name: string;
  onSave: (name: string) => void;
}

export default function InlineTeamNameEditor({ name, onSave }: Props) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(name);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setValue(name);
  }, [name]);

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing]);

  function validate(v: string): string | null {
    const trimmed = v.trim();
    if (trimmed.length < 3) return "Name must be at least 3 characters.";
    if (trimmed.length > 64) return "Name must be 64 characters or fewer.";
    if (!NAME_REGEX.test(trimmed)) return "Only letters, digits, spaces, hyphens, and underscores.";
    return null;
  }

  function commit() {
    const trimmed = value.trim();
    const err = validate(trimmed);
    if (err) {
      setError(err);
      return;
    }
    setError(null);
    setEditing(false);
    if (trimmed !== name) {
      onSave(trimmed);
    }
  }

  function cancel() {
    setValue(name);
    setError(null);
    setEditing(false);
  }

  if (!editing) {
    return (
      <button
        className="group flex items-center gap-2 text-left"
        onClick={() => setEditing(true)}
        type="button"
      >
        <h2 className="font-display text-lg font-semibold text-ink group-hover:text-tide transition-colors">
          {name || "Untitled Team"}
        </h2>
        <span className="opacity-0 group-hover:opacity-60 transition-opacity text-ink text-sm">
          ✏
        </span>
      </button>
    );
  }

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-2">
        <input
          ref={inputRef}
          className="rounded-xl border border-tide px-2 py-1 font-display text-lg font-semibold text-ink focus:outline-none focus:ring-2 focus:ring-tide/30 w-64"
          maxLength={64}
          onBlur={commit}
          onChange={(e) => {
            setValue(e.target.value);
            setError(validate(e.target.value.trim()));
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") commit();
            if (e.key === "Escape") cancel();
          }}
          type="text"
          value={value}
        />
      </div>
      {error && (
        <p className="text-[11px] text-ember pl-1">{error}</p>
      )}
    </div>
  );
}
