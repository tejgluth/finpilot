import pytest

from backend.config import settings
from backend.database import init_db
from backend.llm.strategy_builder import (
    build_execution_snapshot,
    compile_strategy_conversation,
    create_strategy_conversation,
    default_compiled_team,
    resolve_effective_team,
    save_team_version,
    select_active_team,
)
from backend.models.agent_team import CompiledTeam, DataBoundary
from backend.settings.user_settings import default_user_settings


def offline_user_settings():
    settings = default_user_settings()
    settings.llm.provider = "ollama"
    settings.llm.ollama_base_url = "http://127.0.0.1:9"
    settings.llm.ollama_model = "llama3.2"
    return settings


@pytest.fixture(autouse=True)
async def isolated_strategy_state(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "db_path", tmp_path / "strategy.db")
    await init_db()


@pytest.mark.asyncio
async def test_conversation_compile_produces_prompt_specific_team_shapes():
    settings = offline_user_settings()
    value_conversation = await create_strategy_conversation(settings)
    momentum_conversation = await create_strategy_conversation(settings)

    from backend.llm.strategy_builder import process_strategy_message

    await process_strategy_message(
        value_conversation.conversation_id,
        "Build a conservative long-term dividend value team for healthcare and keep sentiment secondary.",
        True,
        settings,
    )
    await process_strategy_message(
        momentum_conversation.conversation_id,
        "Build an aggressive short-term semiconductor breakout team inspired by O'Neil and Minervini, avoid financials.",
        True,
        settings,
    )

    _, _, value_compiled, _ = await compile_strategy_conversation(value_conversation.conversation_id, settings)
    _, _, momentum_compiled, _ = await compile_strategy_conversation(momentum_conversation.conversation_id, settings)

    assert value_compiled.risk_level == "conservative"
    assert value_compiled.time_horizon == "long"
    assert momentum_compiled.risk_level == "aggressive"
    assert momentum_compiled.time_horizon == "short"
    assert value_compiled.agent_weights.get("sentiment", 100) <= 20
    assert momentum_compiled.compiled_agent_specs["technicals"].variant_id == "oneil_breakout"
    assert momentum_compiled.compiled_agent_specs["momentum"].variant_id in {
        "oneil_leader_tracking",
        "minervini_breakout_quality",
    }


@pytest.mark.asyncio
async def test_conversation_filters_compile_into_bounded_modifiers():
    settings = offline_user_settings()
    conversation = await create_strategy_conversation(settings)

    from backend.llm.strategy_builder import process_strategy_message

    await process_strategy_message(
        conversation.conversation_id,
        (
            "Build a moderate medium-term team with news first sentiment, reddit lookback 24 hours, "
            "technical lookback 180 days, defensive tilt on macro, benchmark heavy momentum, "
            "and growth floor 15%."
        ),
        True,
        settings,
    )

    _, _, compiled, _ = await compile_strategy_conversation(conversation.conversation_id, settings)

    assert compiled.compiled_agent_specs["sentiment"].modifiers["source_weighting"] == "news_first"
    assert compiled.compiled_agent_specs["sentiment"].modifiers["reddit_lookback_hours"] == 24
    assert compiled.compiled_agent_specs["technicals"].modifiers["lookback_days"] == 180
    assert compiled.compiled_agent_specs["macro"].modifiers["defensive_tilt"] is True
    assert compiled.compiled_agent_specs["momentum"].modifiers["benchmark_weight"] == "high"
    assert compiled.compiled_agent_specs["growth"].modifiers["growth_floor"] == 0.15


@pytest.mark.asyncio
async def test_team_versions_are_immutable_and_increment():
    compiled = default_compiled_team().model_copy(deep=True)
    compiled.team_id = "team-test-versioning"
    compiled.version_number = 0

    first = await save_team_version(compiled, conversation_id=None, label="Draft A")
    second = await save_team_version(compiled, conversation_id=None, label="Draft B")

    assert first.version_number == 1
    assert second.version_number == 2
    assert first.content_hash == second.content_hash


@pytest.mark.asyncio
async def test_explicit_team_config_takes_precedence_over_active_team():
    settings = offline_user_settings()
    default_team = default_compiled_team()
    default_team.team_id = "team-precedence"
    default_team.version_number = 0
    version = await save_team_version(default_team, conversation_id=None, label="Persisted")
    await select_active_team(version.team_id, version.version_number)

    explicit = default_compiled_team().model_copy(deep=True)
    explicit.team_id = "team-explicit"
    explicit.name = "Explicit Override"

    resolved = await resolve_effective_team(
        user_settings=settings,
        team_config=explicit,
        team_id=version.team_id,
        version_number=version.version_number,
    )

    assert isinstance(resolved, CompiledTeam)
    assert resolved.team_id == "team-explicit"
    assert resolved.name == "Explicit Override"


def test_execution_snapshot_marks_strict_temporal_mode():
    settings = offline_user_settings()
    snapshot = build_execution_snapshot(
        mode="backtest_strict",
        ticker_or_universe="AAPL",
        user_settings=settings,
        compiled_team=default_compiled_team(),
        data_boundary=DataBoundary(
            mode="backtest_strict",
            as_of_datetime="2025-01-03T21:00:00+00:00",
            allow_latest_semantics=False,
        ),
        cost_model={"slippage_pct": 0.1},
        notes=[],
    )

    assert snapshot.strict_temporal_mode is True
    assert snapshot.data_boundary.as_of_datetime == "2025-01-03T21:00:00+00:00"
