from backend.llm.capability_catalog import build_capability_gaps
from backend.settings.user_settings import default_user_settings


def test_capability_gap_stays_missing_when_toggle_is_enabled_but_key_is_absent(monkeypatch):
    settings = default_user_settings()
    settings.data_sources.use_fmp = True

    monkeypatch.setattr("backend.llm.capability_catalog.env_settings.fmp_api_key", "")

    gaps = build_capability_gaps("fundamentals", settings)

    earnings_gap = next(gap for gap in gaps if gap.capability_id == "earnings_execution_history")
    assert earnings_gap.status == "missing_key"


def test_capability_gap_disappears_once_key_backed_source_is_really_available(monkeypatch):
    settings = default_user_settings()
    settings.data_sources.use_fmp = True

    monkeypatch.setattr("backend.llm.capability_catalog.env_settings.fmp_api_key", "live-key")

    gaps = build_capability_gaps("fundamentals", settings)

    assert all(gap.capability_id != "earnings_execution_history" for gap in gaps)
