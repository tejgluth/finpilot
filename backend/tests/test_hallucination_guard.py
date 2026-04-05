import pytest

from datetime import UTC, datetime

from backend.agents.base_agent import BaseAnalysisAgent, FetchedData
from backend.models.agent_team import CompiledAgentSpec, DataBoundary, ExecutionSnapshot
from backend.llm.budget import BudgetTracker
from backend.settings.user_settings import DataSourceSettings, LlmSettings


class DummyAgent(BaseAnalysisAgent):
    agent_name = "dummy"
    EXPECTED_FIELDS = ["present", "missing"]

    async def fetch_data(
        self,
        ticker: str,
        data_settings: DataSourceSettings,
        compiled_spec: CompiledAgentSpec,
        execution_snapshot: ExecutionSnapshot,
    ) -> FetchedData:
        data = FetchedData(ticker=ticker)
        data.fields["present"] = 42
        data.field_sources["present"] = "test"
        data.field_ages["present"] = 5
        return data

    def build_system_prompt(self) -> str:
        return "Test prompt."

    def fallback_assessment(
        self,
        ticker: str,
        data: FetchedData,
        compiled_spec: CompiledAgentSpec,
    ) -> tuple[str, float, str]:
        return "BUY", 0.8, "Using only the present field."


def _compiled_spec() -> CompiledAgentSpec:
    return CompiledAgentSpec(
        agent_name="fundamentals",
        enabled=True,
        weight=50,
        prompt_pack_id="fundamentals-core",
        prompt_pack_version="1.0.0",
        variant_id="balanced",
        modifiers={},
        owned_sources=["yfinance"],
        freshness_limit_minutes=60,
        lookback_config={},
    )


def _execution_snapshot() -> ExecutionSnapshot:
    from backend.models.agent_team import CompiledTeam

    spec = _compiled_spec()
    return ExecutionSnapshot(
        mode="analyze",
        created_at=datetime.now(UTC).isoformat(),
        ticker_or_universe="AAPL",
        effective_team=CompiledTeam(
            team_id="test-team",
            name="Test Team",
            description="Test team for hallucination guard coverage.",
            enabled_agents=["fundamentals", "risk_manager", "portfolio_manager"],
            agent_weights={"fundamentals": 50},
            compiled_agent_specs={"fundamentals": spec},
            risk_level="moderate",
            time_horizon="medium",
        ),
        provider="fallback",
        model="fallback",
        prompt_pack_versions={"fundamentals": "fundamentals-core@1.0.0"},
        settings_hash="settings",
        team_hash="team",
        data_boundary=DataBoundary(mode="live", allow_latest_semantics=True),
        cost_model={},
    )


def test_build_data_context_marks_unavailable_fields():
    agent = DummyAgent()
    data = FetchedData(ticker="AAPL")
    data.fields["present"] = 42
    data.field_sources["present"] = "test"
    data.field_ages["present"] = 5
    context = agent.build_data_context(data, _compiled_spec(), _execution_snapshot())
    assert "[NOT AVAILABLE" in context


@pytest.mark.asyncio
async def test_confidence_is_penalized_by_coverage():
    agent = DummyAgent()
    signal = await agent.analyze(
        ticker="AAPL",
        data_settings=DataSourceSettings(max_data_age_minutes=60),
        llm_settings=LlmSettings(),
        budget=BudgetTracker(max_cost_usd=1.0, max_tokens=4000),
        compiled_spec=_compiled_spec(),
        execution_snapshot=_execution_snapshot(),
    )
    assert signal.raw_confidence == 0.8
    assert signal.final_confidence < signal.raw_confidence
