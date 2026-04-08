"""
Schema validation for all model outputs.
OWASP LLM02: Insecure Output Handling prevention.
"""

from __future__ import annotations

import json
import re
from typing import TypeVar

from pydantic import BaseModel
from pydantic_core import from_json

ModelT = TypeVar("ModelT", bound=BaseModel)


def parse_llm_json(raw: str, model_class: type[ModelT], *, allow_partial: bool = False) -> ModelT:
    text = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as first_exc:
        if allow_partial:
            try:
                data = from_json(text.encode("utf-8"), allow_partial=True)
            except ValueError:
                data = None
            if isinstance(data, dict):
                try:
                    return model_class.model_validate(data)
                except Exception:
                    pass
        # Some providers (e.g. Anthropic) return prose with JSON embedded.
        # Try to extract the outermost JSON object from the response.
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError as exc:
                if allow_partial:
                    try:
                        partial = from_json(match.group().encode("utf-8"), allow_partial=True)
                    except ValueError:
                        partial = None
                    if isinstance(partial, dict):
                        try:
                            return model_class.model_validate(partial)
                        except Exception:
                            pass
                raise ValueError(f"LLM returned invalid JSON: {exc}. Raw: {text[:300]!r}") from exc
        else:
            raise ValueError(f"LLM returned invalid JSON: {first_exc}. Raw: {text[:300]!r}") from first_exc
    try:
        return model_class.model_validate(data)
    except Exception as exc:  # pragma: no cover - surfaced to callers
        raise ValueError(
            f"LLM output failed {model_class.__name__} validation: {exc}"
        ) from exc


__all__ = ["parse_llm_json"]
