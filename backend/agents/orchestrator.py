from __future__ import annotations

import asyncio

from backend.agents.analysis import (
    FundamentalsAgent,
    GrowthAgent,
    MacroAgent,
    MomentumAgent,
    SentimentAgent,
    TechnicalsAgent,
    ValueAgent,
)
from backend.agents.debate.bear_researcher import build_bear_case
from backend.agents.debate.bull_researcher import build_bull_case
from backend.agents.decision.portfolio_manager import decide_portfolio_action
from backend.agents.decision.risk_manager import evaluate_risk
from backend.agents.graph_runtime import run_graph_pipeline
from backend.llm.budget import BudgetTracker
from backend.models.agent_team import ExecutionSnapshot
from backend.models.signal import AgentSignal, DebateOutput, PortfolioDecision
from backend.settings.user_settings import UserSettings


AGENT_FACTORY = {
    "fundamentals": FundamentalsAgent,
    "technicals": TechnicalsAgent,
    "sentiment": SentimentAgent,
    "macro": MacroAgent,
    "value": ValueAgent,
    "momentum": MomentumAgent,
    "growth": GrowthAgent,
}


async def run_agent_pipeline(
    ticker: str,
    runtime_settings: UserSettings,
    execution_snapshot: ExecutionSnapshot,
    budget: BudgetTracker | None = None,
) -> tuple[list[AgentSignal], DebateOutput | None, DebateOutput | None, PortfolioDecision]:
    budget = budget or BudgetTracker(
        max_cost_usd=runtime_settings.llm.max_cost_per_session_usd,
        max_tokens=runtime_settings.llm.max_tokens_per_request,
    )
    team = execution_snapshot.effective_team
    if team.team_classification in {"validated_custom", "experimental_custom"} and team.topology is not None:
        return await run_graph_pipeline(
            ticker=ticker,
            runtime_settings=runtime_settings,
            execution_snapshot=execution_snapshot,
            budget=budget,
        )
    enabled = {
        "fundamentals": runtime_settings.agents.enable_fundamentals,
        "technicals": runtime_settings.agents.enable_technicals,
        "sentiment": runtime_settings.agents.enable_sentiment,
        "macro": runtime_settings.agents.enable_macro,
        "value": runtime_settings.agents.enable_value,
        "momentum": runtime_settings.agents.enable_momentum,
        "growth": runtime_settings.agents.enable_growth,
    }
    names = [
        name
        for name in team.enabled_agents
        if name in AGENT_FACTORY and enabled.get(name, False) and name in team.compiled_agent_specs
    ]
    tasks = [
        AGENT_FACTORY[name]().analyze(
            ticker=ticker,
            data_settings=runtime_settings.data_sources,
            llm_settings=runtime_settings.llm,
            budget=budget,
            compiled_spec=team.compiled_agent_specs[name],
            execution_snapshot=execution_snapshot,
        )
        for name in names
    ]
    signals = await asyncio.gather(*tasks) if tasks else []
    bull_case = build_bull_case(signals) if runtime_settings.agents.enable_bull_bear_debate else None
    bear_case = build_bear_case(signals) if runtime_settings.agents.enable_bull_bear_debate else None
    risk = evaluate_risk(signals, runtime_settings.guardrails, runtime_settings.agents)
    decision = decide_portfolio_action(
        ticker=ticker,
        signals=signals,
        bull_case=bull_case,
        bear_case=bear_case,
        proposed_position_pct=risk.proposed_position_pct,
        agent_weights=team.agent_weights,
        risk_notes=risk.notes if risk.allowed else f"Trade blocked: {risk.notes}",
        max_data_age_minutes=runtime_settings.data_sources.max_data_age_minutes,
    )
    if not risk.allowed:
        decision.action = "HOLD"
        decision.proposed_position_pct = 0.0
    return signals, bull_case, bear_case, decision
