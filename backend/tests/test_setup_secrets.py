from pathlib import Path

from backend.security.secrets import read_env_values, write_onboarding_env_values


def test_write_onboarding_env_values_updates_existing_file(tmp_path: Path):
    env_path = tmp_path / ".env"
    env_path.write_text("OPENAI_API_KEY=old\nAI_PROVIDER=openai\n", encoding="utf-8")

    saved = write_onboarding_env_values(
        {"OPENAI_API_KEY": "new-secret", "AI_PROVIDER": "anthropic"},
        env_path=env_path,
    )

    values = read_env_values(env_path)
    assert saved == ["AI_PROVIDER", "OPENAI_API_KEY"]
    assert values["OPENAI_API_KEY"] == "new-secret"
    assert values["AI_PROVIDER"] == "anthropic"


def test_write_onboarding_env_values_quotes_values_with_spaces(tmp_path: Path):
    env_path = tmp_path / ".env"
    env_path.write_text("REDDIT_USER_AGENT=\n", encoding="utf-8")

    write_onboarding_env_values(
        {"REDDIT_USER_AGENT": "finpilot:v0.1 (by /u/tester)"},
        env_path=env_path,
    )

    contents = env_path.read_text(encoding="utf-8")
    assert 'REDDIT_USER_AGENT="finpilot:v0.1 (by /u/tester)"' in contents
    assert read_env_values(env_path)["REDDIT_USER_AGENT"] == "finpilot:v0.1 (by /u/tester)"


def test_write_onboarding_env_values_removes_duplicate_onboarding_keys(tmp_path: Path):
    env_path = tmp_path / ".env"
    env_path.write_text("AI_PROVIDER=openai\nAI_PROVIDER=google\nALPACA_MODE=paper\n", encoding="utf-8")

    write_onboarding_env_values({"AI_PROVIDER": "ollama"}, env_path=env_path)

    contents = env_path.read_text(encoding="utf-8")
    assert contents.count("AI_PROVIDER=") == 1
    assert "AI_PROVIDER=ollama" in contents


def test_write_onboarding_env_values_rejects_unknown_keys(tmp_path: Path):
    env_path = tmp_path / ".env"
    env_path.write_text("", encoding="utf-8")

    try:
        write_onboarding_env_values({"UNSAFE_KEY": "value"}, env_path=env_path)
    except ValueError as exc:
        assert "Unsupported environment keys" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected a ValueError for unknown keys")
