import pytest

from backend.llm.budget import BudgetTracker
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
    assert client.available is True


@pytest.mark.asyncio
async def test_ollama_chat_falls_back_to_generate_on_404(monkeypatch):
    settings = LlmSettings(provider="ollama", model="gemma4", ollama_base_url="http://localhost:11434")
    client = get_llm_client(settings)

    class MockResponse:
        def __init__(self, status_code: int, payload: dict):
            self.status_code = status_code
            self._payload = payload

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError(f"status {self.status_code}")

        def json(self):
            return self._payload

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            self.calls = []

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json):
            self.calls.append((url, json))
            if url.endswith("/api/chat"):
                return MockResponse(404, {"error": "not found"})
            if url.endswith("/api/generate"):
                return MockResponse(200, {"response": '{"ok": true}'})
            raise AssertionError(f"unexpected url {url}")

    monkeypatch.setattr("backend.llm.provider.httpx.AsyncClient", MockAsyncClient)
    content = await client.chat(
        system="Return JSON.",
        messages=[{"role": "user", "content": "hello"}],
        max_tokens=200,
        temperature=0.2,
        budget=BudgetTracker(max_cost_usd=1.0, max_tokens=1000),
    )
    assert content == '{"ok": true}'
