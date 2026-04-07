from backend.llm.provider import _default_model
from backend.settings.user_settings import LlmSettings


def test_ollama_prefers_generic_model_override():
    settings = LlmSettings(provider="ollama", model="gemma4", ollama_model="llama3.2")
    assert _default_model("ollama", settings) == "gemma4"
