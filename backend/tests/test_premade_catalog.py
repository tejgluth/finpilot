from __future__ import annotations

import pytest

from backend.llm.premade_catalog import get_catalog, get_default_template, get_premade_team
from backend.llm.prompt_packs import PROMPT_PACKS_BY_AGENT
from backend.llm.strategy_builder import compile_from_template
from backend.llm.team_matching import match_team
from backend.models.agent_team import (
    REQUIRED_DECISION_AGENTS,
    VALID_ANALYSIS_AGENTS,
    VALID_SECTORS,
    PremadeTeamCatalog,
    PremadeTeamTemplate,
    StrategyPreferences,
)


# ── Catalog integrity ────────────────────────────────────────────────────────

def test_catalog_loads_without_error():
    catalog = get_catalog()
    assert isinstance(catalog, PremadeTeamCatalog)


def test_catalog_has_exactly_18_teams():
    assert len(get_catalog().teams) == 18


def test_team_ids_are_unique():
    ids = [t.team_id for t in get_catalog().teams]
    assert len(ids) == len(set(ids))


def test_exactly_one_default_team():
    defaults = [t for t in get_catalog().teams if t.is_default]
    assert len(defaults) == 1
    assert defaults[0].team_id == "balanced-core"


def test_default_team_id_field_matches_default_team():
    catalog = get_catalog()
    assert catalog.default_team_id == "balanced-core"
    default_team = get_default_template()
    assert default_team.team_id == catalog.default_team_id


def test_featured_team_ids_exist_in_catalog():
    catalog = get_catalog()
    team_ids = {t.team_id for t in catalog.teams}
    for fid in catalog.featured_team_ids:
        assert fid in team_ids, f"featured_team_id '{fid}' not found in catalog"


def test_hidden_team_ids_exist_in_catalog():
    catalog = get_catalog()
    team_ids = {t.team_id for t in catalog.teams}
    for hid in catalog.hidden_team_ids:
        assert hid in team_ids, f"hidden_team_id '{hid}' not found in catalog"


def test_exactly_3_featured_teams():
    assert len(get_catalog().featured_team_ids) == 3


def test_exactly_5_hidden_teams():
    assert len(get_catalog().hidden_team_ids) == 5


# ── Team validity ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("team", get_catalog().teams)
def test_team_has_at_least_one_analysis_agent(team: PremadeTeamTemplate):
    assert len(team.enabled_analysis_agents) >= 1


@pytest.mark.parametrize("team", get_catalog().teams)
def test_team_analysis_agents_are_valid(team: PremadeTeamTemplate):
    invalid = set(team.enabled_analysis_agents) - VALID_ANALYSIS_AGENTS
    assert not invalid, f"{team.team_id}: invalid agents {invalid}"


@pytest.mark.parametrize("team", get_catalog().teams)
def test_team_weights_in_range(team: PremadeTeamTemplate):
    for agent, weight in team.weights.items():
        assert 0 <= weight <= 100, f"{team.team_id}: {agent} weight {weight} out of range"


@pytest.mark.parametrize("team", get_catalog().teams)
def test_team_weight_keys_are_analysis_agents(team: PremadeTeamTemplate):
    invalid = set(team.weights.keys()) - VALID_ANALYSIS_AGENTS
    assert not invalid, f"{team.team_id}: weight keys not in VALID_ANALYSIS_AGENTS: {invalid}"


@pytest.mark.parametrize("team", get_catalog().teams)
def test_team_variant_keys_are_enabled_agents(team: PremadeTeamTemplate):
    enabled = set(team.enabled_analysis_agents)
    for agent in team.agent_variants:
        assert agent in enabled, f"{team.team_id}: variant key '{agent}' is not an enabled agent"


@pytest.mark.parametrize("team", get_catalog().teams)
def test_team_variants_exist_in_prompt_packs(team: PremadeTeamTemplate):
    for agent, variant_id in team.agent_variants.items():
        pack = PROMPT_PACKS_BY_AGENT.get(agent)
        assert pack is not None, f"{team.team_id}: no pack for agent '{agent}'"
        valid_ids = {v.variant_id for v in pack.allowed_variants}
        assert variant_id in valid_ids, (
            f"{team.team_id}: variant '{agent}:{variant_id}' not in pack. "
            f"Valid: {sorted(valid_ids)}"
        )


@pytest.mark.parametrize("team", get_catalog().teams)
def test_team_excluded_sectors_are_valid(team: PremadeTeamTemplate):
    invalid = set(team.excluded_sectors) - VALID_SECTORS
    assert not invalid, f"{team.team_id}: invalid sectors {invalid}"


@pytest.mark.parametrize("team", get_catalog().teams)
def test_team_confidence_threshold_in_range(team: PremadeTeamTemplate):
    threshold = team.team_overrides.get("min_confidence_threshold", 0.55)
    assert 0.3 <= float(threshold) <= 0.9, (
        f"{team.team_id}: min_confidence_threshold {threshold} out of 0.3-0.9 range"
    )


@pytest.mark.parametrize("team", get_catalog().teams)
def test_no_crypto_references(team: PremadeTeamTemplate):
    combined = " ".join([team.team_id, team.description.lower(), team.target_user.lower()])
    assert "crypto" not in combined, f"{team.team_id}: contains crypto reference"


# ── Non-overlap ───────────────────────────────────────────────────────────────

def test_no_two_teams_have_identical_variant_combination():
    combos: list[frozenset] = []
    for team in get_catalog().teams:
        combo = frozenset(team.agent_variants.items())
        assert combo not in combos, (
            f"Duplicate agent_variants combination found on {team.team_id}"
        )
        combos.append(combo)


def test_no_two_teams_have_identical_weight_risk_horizon_signature():
    sigs: list[tuple] = []
    for team in get_catalog().teams:
        sig = (frozenset(team.weights.items()), team.risk_level, team.time_horizon)
        assert sig not in sigs, (
            f"Duplicate (weights, risk, horizon) signature on {team.team_id}"
        )
        sigs.append(sig)


# ── Prompt packs ──────────────────────────────────────────────────────────────

def test_each_analysis_agent_has_a_pack():
    for agent in VALID_ANALYSIS_AGENTS:
        assert agent in PROMPT_PACKS_BY_AGENT, f"No prompt pack for agent '{agent}'"


def test_each_pack_has_balanced_variant():
    for agent, pack in PROMPT_PACKS_BY_AGENT.items():
        ids = {v.variant_id for v in pack.allowed_variants}
        assert "balanced" in ids, f"Pack '{agent}' missing 'balanced' variant"


def test_each_pack_has_at_least_4_variants():
    for agent, pack in PROMPT_PACKS_BY_AGENT.items():
        assert len(pack.allowed_variants) >= 4, (
            f"Pack '{agent}' has only {len(pack.allowed_variants)} variants"
        )


def test_macro_pack_has_rates_regime_variant():
    macro_pack = PROMPT_PACKS_BY_AGENT["macro"]
    ids = {v.variant_id for v in macro_pack.allowed_variants}
    assert "rates_regime" in ids, "macro pack missing 'rates_regime' variant"


def test_all_packs_include_required_forbidden_capabilities():
    required = {"invent_new_data", "invent_new_tools", "ignore_data_boundary", "cross_agent_domain_access"}
    for agent, pack in PROMPT_PACKS_BY_AGENT.items():
        missing = required - set(pack.forbidden_capabilities)
        assert not missing, f"Pack '{agent}' missing forbidden capabilities: {missing}"


def test_variant_ids_unique_within_pack():
    for agent, pack in PROMPT_PACKS_BY_AGENT.items():
        ids = [v.variant_id for v in pack.allowed_variants]
        assert len(ids) == len(set(ids)), f"Duplicate variant_ids in '{agent}' pack"


# ── Compilation integration ───────────────────────────────────────────────────

@pytest.mark.parametrize("team", get_catalog().teams)
def test_all_premade_teams_compile_without_error(team: PremadeTeamTemplate):
    compiled = compile_from_template(team)
    assert compiled.validation_report.valid is True
    assert compiled.team_id == team.team_id


@pytest.mark.parametrize("team", get_catalog().teams)
def test_compiled_teams_include_required_decision_agents(team: PremadeTeamTemplate):
    compiled = compile_from_template(team)
    enabled = set(compiled.enabled_agents)
    for required in REQUIRED_DECISION_AGENTS:
        assert required in enabled, (
            f"{team.team_id}: compiled team missing required agent '{required}'"
        )


@pytest.mark.parametrize("team", get_catalog().teams)
def test_compiled_weights_in_range(team: PremadeTeamTemplate):
    compiled = compile_from_template(team)
    for agent, weight in compiled.agent_weights.items():
        assert 0 <= weight <= 100, (
            f"{team.team_id}: compiled weight for '{agent}' is {weight}"
        )


# ── Matching logic ────────────────────────────────────────────────────────────

def test_match_empty_preferences_falls_back_to_default():
    prefs = StrategyPreferences()
    rec = match_team(prefs)
    assert rec.is_fallback_to_default is True
    assert rec.recommended_team_id == "balanced-core"


def test_match_crypto_returns_error():
    prefs = StrategyPreferences(asset_universe="crypto")
    rec = match_team(prefs)
    assert rec.recommended_team_id is None
    assert rec.error_code == "crypto_not_supported_v1"
    assert "crypto_not_supported_v1" in rec.explanation.contradictions_detected


def test_match_dividend_style_tag_returns_income_team():
    prefs = StrategyPreferences(
        risk_level="conservative",
        time_horizon="long",
        style_tags=["dividend"],
    )
    rec = match_team(prefs)
    assert rec.recommended_team_id == "dividend-income"


def test_match_aggressive_momentum_returns_momentum_team():
    prefs = StrategyPreferences(
        risk_level="aggressive",
        time_horizon="short",
        preferred_factors=["momentum"],
    )
    rec = match_team(prefs)
    assert rec.recommended_team_id in {"momentum-leader", "trend-template"}


def test_match_returns_follow_up_when_both_dimensions_missing():
    prefs = StrategyPreferences(preferred_factors=["value"])
    rec = match_team(prefs)
    # Should ask for risk and/or horizon since both are unresolved
    if "risk_level" in prefs.unresolved_items and "time_horizon" in prefs.unresolved_items:
        assert rec.follow_up_question is not None


def test_match_contradiction_aggressive_plus_income_flags_warning():
    prefs = StrategyPreferences(
        risk_level="aggressive",
        preferred_factors=["income"],
    )
    rec = match_team(prefs)
    assert len(rec.explanation.contradictions_detected) > 0


def test_match_is_stable_for_same_input():
    prefs = StrategyPreferences(
        risk_level="aggressive",
        time_horizon="short",
        preferred_factors=["momentum"],
    )
    r1 = match_team(prefs)
    r2 = match_team(prefs)
    assert r1.recommended_team_id == r2.recommended_team_id


def test_match_returns_alternatives():
    prefs = StrategyPreferences(
        risk_level="moderate",
        time_horizon="long",
        preferred_factors=["value"],
    )
    rec = match_team(prefs)
    assert len(rec.alternatives) >= 1


def test_get_premade_team_returns_none_for_unknown_id():
    assert get_premade_team("does-not-exist") is None


def test_get_premade_team_returns_correct_template():
    template = get_premade_team("balanced-core")
    assert template is not None
    assert template.is_default is True
