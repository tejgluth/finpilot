import pytest

from backend.llm.budget import BudgetTracker
from backend.llm.provider import get_llm_client
from backend.settings.user_settings import LlmSettings


def test_openai_client_requires_key(monkeypatch):
    monkeypatch.setattr("backend.llm.provider.env_settings.openai_api_key", "")
    client = get_llm_client(LlmSettings(provider="openai"))
    assert client.provider_name == "openai"
    assert client.available is False


def test_google_client_requires_key(monkeypatch):
    monkeypatch.setattr("backend.llm.provider.env_settings.google_api_key", "")
    client = get_llm_client(LlmSettings(provider="google"))
    assert client.provider_name == "google"
    assert client.available is False


@pytest.mark.asyncio
async def test_openai_chat_uses_json_object_payload(monkeypatch):
    monkeypatch.setattr("backend.llm.provider.env_settings.openai_api_key", "openai-key")
    client = get_llm_client(LlmSettings(provider="openai", model="gpt-4o-mini"))

    captured: dict[str, object] = {}

    class MockResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": '{"ok": true}'}}]}

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return MockResponse()

    monkeypatch.setattr("backend.llm.provider.httpx.AsyncClient", MockAsyncClient)

    content = await client.chat(
        system="Return JSON.",
        messages=[{"role": "user", "content": "hello"}],
        max_tokens=200,
        temperature=0.2,
        budget=BudgetTracker(max_cost_usd=1.0, max_tokens=1000),
    )

    assert content == '{"ok": true}'
    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["json"]["response_format"] == {"type": "json_object"}
    assert captured["json"]["messages"][0]["role"] == "system"


@pytest.mark.asyncio
async def test_google_chat_uses_generate_content_json_mode_and_role_mapping(monkeypatch):
    monkeypatch.setattr("backend.llm.provider.env_settings.google_api_key", "google-key")
    client = get_llm_client(LlmSettings(provider="google", model="gemini-2.0-flash"))

    captured: dict[str, object] = {}

    class MockResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": '{"ok": true}'}]}}]}

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json=None):
            captured["url"] = url
            captured["json"] = json
            return MockResponse()

    monkeypatch.setattr("backend.llm.provider.httpx.AsyncClient", MockAsyncClient)

    content = await client.chat(
        system="Return JSON.",
        messages=[
          {"role": "user", "content": "hello"},
          {"role": "assistant", "content": "hi"},
        ],
        max_tokens=200,
        temperature=0.2,
        budget=BudgetTracker(max_cost_usd=1.0, max_tokens=1000),
    )

    assert content == '{"ok": true}'
    assert "models/gemini-2.0-flash:generateContent" in str(captured["url"])
    assert captured["json"]["generationConfig"]["responseMimeType"] == "application/json"
    assert captured["json"]["contents"][0]["role"] == "user"
    assert captured["json"]["contents"][1]["role"] == "model"
