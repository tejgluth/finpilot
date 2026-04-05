import pytest

from backend.models.signal import AgentSignal
from backend.security.output_validator import parse_llm_json


def test_parse_llm_json_validates_agent_signal():
    raw = """
    {
      "ticker": "AAPL",
      "agent_name": "fundamentals",
      "action": "BUY",
      "raw_confidence": 0.7,
      "final_confidence": 0.0,
      "reasoning": "Grounded in fetched profitability data.",
      "cited_data": [],
      "unavailable_fields": [],
      "data_coverage_pct": 1.0,
      "oldest_data_age_minutes": 5,
      "warning": ""
    }
    """
    parsed = parse_llm_json(raw, AgentSignal)
    assert parsed.ticker == "AAPL"
    assert parsed.action == "BUY"


def test_parse_llm_json_rejects_invalid_json():
    with pytest.raises(ValueError):
        parse_llm_json("{not-json}", AgentSignal)
