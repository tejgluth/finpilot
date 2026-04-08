from backend.llm.provider import _default_model, get_llm_client
from backend.settings.user_settings import LlmSettings


def test_ollama_prefers_generic_model_override():
    settings = LlmSettings(provider="ollama", model="gemma4", ollama_model="llama3.2")
    assert _default_model("ollama", settings) == "gemma4"


def test_ollama_probe_failures_still_allow_attempt(monkeypatch):
    settings = LlmSettings(provider="ollama", model="gemma4", ollama_base_url="http://localhost:11434")
    monkeypatch.setattr("backend.llm.provider._ollama_model_available", lambda *_args, **_kwargs: None)
    client = get_llm_client(settings)
    assert client.provider_name == "ollama"
    assert client.available is True


def test_ollama_reports_unavailable_when_model_missing(monkeypatch):
    settings = LlmSettings(provider="ollama", model="gemma4", ollama_base_url="http://localhost:11434")
    monkeypatch.setattr("backend.llm.provider._ollama_model_available", lambda *_args, **_kwargs: False)
    client = get_llm_client(settings)
    assert client.provider_name == "ollama"
    assert client.available is False
