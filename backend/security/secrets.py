from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import re
import shutil


SUSPECT_KEY_PATTERN = re.compile(r"(api[_-]?key|secret|token|password)", re.IGNORECASE)
ENV_ASSIGNMENT_PATTERN = re.compile(r"^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$")

ENV_PATH = Path(".env")
ENV_TEMPLATE_PATH = Path(".env.example")
ONBOARDING_ENV_KEYS = {
    "AI_PROVIDER",
    "AI_MODEL",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "ALPACA_API_KEY",
    "ALPACA_SECRET_KEY",
    "ALPACA_MODE",
    "FINNHUB_API_KEY",
    "MARKETAUX_API_KEY",
    "FMP_API_KEY",
    "FRED_API_KEY",
    "REDDIT_CLIENT_ID",
    "REDDIT_CLIENT_SECRET",
    "REDDIT_USER_AGENT",
    "POLYGON_API_KEY",
}


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) < 8:
        return "***"
    return value[:4] + "***" + value[-2:]


def validate_secret_present(value: str, label: str) -> tuple[bool, str]:
    if value:
        return True, f"{label} configured"
    return False, f"{label} missing"


def redact_mapping(data: Mapping[str, object]) -> dict[str, object]:
    redacted: dict[str, object] = {}
    for key, value in data.items():
        if SUSPECT_KEY_PATTERN.search(key):
            redacted[key] = mask_secret(str(value))
        elif isinstance(value, Mapping):
            redacted[key] = redact_mapping(value)
        else:
            redacted[key] = value
    return redacted


def ensure_frontend_safe(payload: Mapping[str, object]) -> dict[str, object]:
    return {key: value for key, value in payload.items() if not SUSPECT_KEY_PATTERN.search(key)}


def ensure_env_file(env_path: Path = ENV_PATH, template_path: Path = ENV_TEMPLATE_PATH) -> Path:
    if env_path.exists():
        return env_path
    env_path.parent.mkdir(parents=True, exist_ok=True)
    if template_path.exists():
        shutil.copyfile(template_path, env_path)
    else:
        env_path.touch()
    return env_path


def read_env_values(env_path: Path = ENV_PATH) -> dict[str, str]:
    if not env_path.exists():
        return {}

    values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        match = ENV_ASSIGNMENT_PATTERN.match(line)
        if not match:
            continue
        key = match.group(1)
        value = match.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        value = value.replace('\\"', '"').replace("\\\\", "\\")
        values[key] = value
    return values


def serialize_env_value(value: str) -> str:
    if value == "":
        return ""
    if re.fullmatch(r"[A-Za-z0-9_./:@-]+", value):
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def write_onboarding_env_values(values: Mapping[str, str], env_path: Path = ENV_PATH) -> list[str]:
    invalid_keys = sorted(set(values) - ONBOARDING_ENV_KEYS)
    if invalid_keys:
        raise ValueError(f"Unsupported environment keys: {', '.join(invalid_keys)}")

    ensure_env_file(env_path=env_path)
    existing_lines = env_path.read_text(encoding="utf-8").splitlines()
    pending = {key: value for key, value in values.items()}
    updated_lines: list[str] = []
    seen_onboarding_keys: set[str] = set()

    for line in existing_lines:
        match = ENV_ASSIGNMENT_PATTERN.match(line)
        if not match:
            updated_lines.append(line)
            continue
        key = match.group(1)
        if key not in ONBOARDING_ENV_KEYS:
            updated_lines.append(line)
            continue

        if key in seen_onboarding_keys:
            continue
        seen_onboarding_keys.add(key)

        if key in pending:
            updated_lines.append(f"{key}={serialize_env_value(pending.pop(key).strip())}")
            continue
        updated_lines.append(line)

    if pending:
        if updated_lines and updated_lines[-1].strip():
            updated_lines.append("")
        for key in sorted(pending):
            updated_lines.append(f"{key}={serialize_env_value(pending[key].strip())}")

    env_path.write_text("\n".join(updated_lines).rstrip() + "\n", encoding="utf-8")
    return sorted(values)
