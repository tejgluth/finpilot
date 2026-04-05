from backend.settings.user_settings import UserSettings, default_user_settings


def test_user_settings_ignore_legacy_guardrail_ceiling_fields_on_load():
    loaded = UserSettings.from_dict(
        {
            "guardrails": {
                "max_position_pct": 6,
                "SYSTEM_MAX_POSITION_PCT": 20,
                "SYSTEM_MAX_TRADES_PER_DAY": 20,
            }
        }
    )

    assert loaded.guardrails.max_position_pct == 6
    assert loaded.guardrails.max_trades_per_day == 5


def test_user_settings_do_not_persist_internal_guardrail_ceiling_fields():
    payload = default_user_settings().to_dict()

    assert "SYSTEM_MAX_POSITION_PCT" not in payload["guardrails"]
    assert "SYSTEM_MAX_SECTOR_PCT" not in payload["guardrails"]
    assert "SYSTEM_MAX_DAILY_LOSS_PCT" not in payload["guardrails"]
    assert "SYSTEM_MAX_TOTAL_DRAWDOWN_PCT" not in payload["guardrails"]
    assert "SYSTEM_MAX_TRADES_PER_DAY" not in payload["guardrails"]
