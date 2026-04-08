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
        if llm_settings and llm_settings.model:
            return llm_settings.model
        return (llm_settings.ollama_model if llm_settings else "") or env_settings.ollama_model
    return "unknown-model"


@lru_cache(maxsize=32)
def _ollama_model_available(base_url: str, model: str) -> bool | None:
    try:
        response = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=2.5)
        response.raise_for_status()
        payload = response.json()
        tags = payload.get("models", [])
        normalized = model.strip().lower()
        for tag in tags:
            name = str(tag.get("name", "")).strip().lower()
            model_name = str(tag.get("model", "")).strip().lower()
            if normalized in {name, model_name}:
                return True
            if normalized and ":" not in normalized and (
                name.startswith(f"{normalized}:") or model_name.startswith(f"{normalized}:")
            ):
                return True
        return False
    except Exception:
        # Local-first Ollama setups can be slow to answer metadata probes even when
        # actual chat requests work. Treat probe failures as "unknown" and let the
        # real chat call determine success.
        return None


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
        base_url = base_url.strip()

        # Support common user-provided variants like:
        # - http://localhost:11434        (default)
        # - http://localhost:11434/api    (API root)
        # - http://localhost:11434/v1     (OpenAI-compat root)
        base = base_url.rstrip("/")
        root_base = base
        openai_base = base
        if base.endswith("/api"):
            root_base = base[: -len("/api")]
            openai_base = root_base
        elif base.endswith("/v1"):
            root_base = base[: -len("/v1")]
            openai_base = base

        chat_url = f"{root_base.rstrip('/')}/api/chat"
        generate_url = f"{root_base.rstrip('/')}/api/generate"
        openai_chat_url = (
            f"{openai_base.rstrip('/')}/chat/completions"
            if openai_base.endswith("/v1")
            else f"{openai_base.rstrip('/')}/v1/chat/completions"
        )

        prompt_parts = [system.strip(), ""]
        for item in messages:
            role = item.get("role", "user").upper()
            content = item.get("content", "").strip()
            prompt_parts.append(f"{role}:\n{content}")
            prompt_parts.append("")
        prompt = "\n".join(prompt_parts).strip()

        chat_payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, *messages],
            "format": "json",
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }

        chat_payload_compat = dict(chat_payload)
        chat_payload_compat.pop("format", None)

        generate_payload = {
            "model": self.model,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        generate_payload_compat = dict(generate_payload)
        generate_payload_compat.pop("format", None)

        openai_payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, *messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
            # Ollama supports OpenAI-compatible endpoints, but response_format support can vary.
            "response_format": {"type": "json_object"},
        }
        openai_payload_compat = dict(openai_payload)
        openai_payload_compat.pop("response_format", None)

        async with httpx.AsyncClient(timeout=90.0) as client:
            # 1) Prefer /api/chat (best structured behavior).
            response = await client.post(chat_url, json=chat_payload)

            # If /api/chat exists but doesn't support format=json yet, retry without format.
            if response.status_code == 400:
                response = await client.post(chat_url, json=chat_payload_compat)

            # 2) Older Ollama versions don't have /api/chat (404). Some proxies respond 405.
            if response.status_code in {404, 405}:
                response = await client.post(generate_url, json=generate_payload)
                if response.status_code == 400:
                    response = await client.post(generate_url, json=generate_payload_compat)

            # 3) Last resort: OpenAI-compatible endpoint.
            if response.status_code in {404, 405}:
                response = await client.post(openai_chat_url, json=openai_payload)
                if response.status_code == 400:
                    response = await client.post(openai_chat_url, json=openai_payload_compat)

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                body = ""
                try:
                    payload = exc.response.json()
                    body = str(payload.get("error") or payload.get("message") or payload)[:300]
                except Exception:
                    body = (exc.response.text or "")[:300]

                hint = ""
                if status_code == 404 and ("model" in body.lower() and "not" in body.lower()):
                    hint = f" Model '{self.model}' is likely not installed. Try: `ollama pull {self.model}`."
                elif status_code in {404, 405}:
                    hint = (
                        " This Ollama instance may be very old or not actually Ollama. "
                        f"Checked endpoints: {chat_url}, {generate_url}, {openai_chat_url}."
                    )

                raise RuntimeError(
                    f"Ollama request failed ({status_code}) at {exc.request.url}. {body}{hint}".strip()
                ) from exc
        data = response.json()
        if "message" in data:
            message = data.get("message", {})
            content = message.get("content", "")
        elif "choices" in data:
            choices = data.get("choices", [])
            if not choices:
                raise RuntimeError("Ollama OpenAI-compatible endpoint returned no choices")
            choice0 = choices[0]
            message = choice0.get("message", {}) if isinstance(choice0, dict) else {}
            content = message.get("content", "") if isinstance(message, dict) else ""
        else:
            content = data.get("response", "")
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
        model = _default_model(provider_name, llm_settings)
        # For local Ollama, a configured base URL + model is enough to attempt a call.
        # Preflight metadata checks are helpful for diagnostics but too brittle to gate usage.
        available = bool(base_url.strip() and model.strip())
    else:
        available = False
    return LLMClient(
        provider_name=provider_name,
        available=available,
        model=_default_model(provider_name, llm_settings),
        llm_settings=llm_settings,
    )
