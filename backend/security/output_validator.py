"""
Schema validation for all model outputs.
OWASP LLM02: Insecure Output Handling prevention.
"""

from __future__ import annotations

import json
import re
from typing import TypeVar

from pydantic import BaseModel

ModelT = TypeVar("ModelT", bound=BaseModel)


def parse_llm_json(raw: str, model_class: type[ModelT]) -> ModelT:
    text = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned invalid JSON: {exc}. Raw: {text[:300]!r}") from exc
    try:
        return model_class.model_validate(data)
    except Exception as exc:  # pragma: no cover - surfaced to callers
        raise ValueError(
            f"LLM output failed {model_class.__name__} validation: {exc}"
        ) from exc


__all__ = ["parse_llm_json"]
