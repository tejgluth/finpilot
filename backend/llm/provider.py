from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING

import httpx

from backend.config import settings as env_settings

if TYPE_CHECKING:  # pragma: no cover
    from backend.settings.user_settings import LlmSettings


def _default_model(provider_name: str, llm_settings: "LlmSettings | None") -> str:
    if llm_settings and llm_settings.model:
        return llm_settings.model
    if provider_name == "openai":
        return env_settings.ai_model or "gpt-4o-mini"
    if provider_name == "anthropic":
        return env_settings.ai_model or "claude-3-5-sonnet-latest"
    if provider_name == "google":
        return env_settings.ai_model or "gemini-2.0-flash"
    if provider_name == "ollama":
        return (llm_settings.ollama_model if llm_settings else "") or env_settings.ollama_model
    return "unknown-model"


@lru_cache(maxsize=8)
def _ollama_available(base_url: str) -> bool:
    try:
        response = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=0.4)
        return response.is_success
    except Exception:
        return False


@dataclass
class LLMClient:
    provider_name: str
    available: bool
    model: str
    llm_settings: "LlmSettings | None" = None

    async def chat(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
        budget,
    ) -> str:
        estimated_tokens = max(1, len(system + "".join(item["content"] for item in messages)) // 4)
        budget.record(min(estimated_tokens, max_tokens), 0.0)
        if not self.available:
            raise RuntimeError(f"Provider {self.provider_name} is not configured")

        if self.provider_name == "openai":
            return await self._openai_chat(system, messages, max_tokens, temperature)
        if self.provider_name == "anthropic":
            return await self._anthropic_chat(system, messages, max_tokens, temperature)
        if self.provider_name == "google":
            return await self._google_chat(system, messages, max_tokens, temperature)
        if self.provider_name == "ollama":
            return await self._ollama_chat(system, messages, max_tokens, temperature)
        raise RuntimeError(f"Unsupported provider: {self.provider_name}")

    async def _openai_chat(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, *messages],
            "response_format": {"type": "json_object"},
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {env_settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def _anthropic_chat(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> str:
        payload = {
            "model": self.model,
            "system": system,
            "messages": [{"role": item["role"], "content": item["content"]} for item in messages],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        headers = {
            "x-api-key": env_settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            response.raise_for_status()
        data = response.json()
        content = data.get("content", [])
        text_parts = [item.get("text", "") for item in content if item.get("type") == "text"]
        return "\n".join(text_parts)

    async def _google_chat(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> str:
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": item["role"], "parts": [{"text": item["content"]}]} for item in messages],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json",
            },
        }
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            f"?key={env_settings.google_api_key}"
        )
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError("Google model returned no candidates")
        return candidates[0]["content"]["parts"][0]["text"]

    async def _ollama_chat(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> str:
        base_url = (self.llm_settings.ollama_base_url if self.llm_settings else "") or env_settings.ollama_base_url
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, *messages],
            "format": "json",
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(f"{base_url.rstrip('/')}/api/chat", json=payload)
            response.raise_for_status()
        data = response.json()
        message = data.get("message", {})
        content = message.get("content", "")
        # Some Ollama models wrap JSON in code fences. Preserve raw text and let validators strip them.
        return content


def get_llm_client(llm_settings: "LlmSettings | None" = None) -> LLMClient:
    provider_name = (llm_settings.provider if llm_settings else env_settings.ai_provider).strip().lower()
    available = True
    if provider_name == "openai":
        available = bool(env_settings.openai_api_key)
    elif provider_name == "anthropic":
        available = bool(env_settings.anthropic_api_key)
    elif provider_name == "google":
        available = bool(env_settings.google_api_key)
    elif provider_name == "ollama":
        base_url = (llm_settings.ollama_base_url if llm_settings else "") or env_settings.ollama_base_url
        available = _ollama_available(base_url)
    else:
        available = False
    return LLMClient(
        provider_name=provider_name,
        available=available,
        model=_default_model(provider_name, llm_settings),
        llm_settings=llm_settings,
    )
