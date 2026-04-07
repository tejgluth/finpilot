from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import ceil, sqrt
from typing import Any

from backend.models.agent_team import CompiledTeam
from backend.models.backtest_result import DecisionEvent
from backend.settings.user_settings import UserSettings


@dataclass
class PortfolioConstructionConfig:
    candidate_pool_size: int
    top_n_holdings: int
    min_conviction_score: float
    min_confidence_threshold: float
    weighting_mode: str
    score_normalization_mode: str
    score_exponent: float
    risk_adjustment_mode: str
    min_position_pct: float
    max_position_pct: float
    cash_floor_pct: float
    max_gross_exposure_pct: float
    sector_cap_pct: float
    selection_buffer_pct: float
    turnover_buffer_pct: float
    max_turnover_pct: float
    hold_zone_pct: float
    replacement_threshold: float
    persistence_bonus: float
    min_price: float
    min_avg_dollar_volume_millions: float
    liquidity_lookback_days: int
    min_history_days: int
    rebalance_frequency_preference: str
    sector_exclusions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ConstructionPlan:
    weights: dict[str, float]
    target_gross_pct: float
    target_cash_pct: float
    average_priority_score: float
    turnover_pct: float
    selected_tickers: list[str]
    excluded_tickers: list[str]
    replaced_tickers: list[str]
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_portfolio_construction_config(
    request: Any,
    user_settings: UserSettings,
    team: CompiledTeam,
) -> PortfolioConstructionConfig:
    defaults = user_settings.backtest
    profile = team.portfolio_construction
    request_fields = set(getattr(request, "input_overrides", []))

    explicit_top_n = {"top_n_holdings", "max_positions", "selection_count"} & set(request_fields)
    if explicit_top_n:
        top_n_holdings = int(
            getattr(request, "top_n_holdings", 0)
            or getattr(request, "max_positions", 0)
            or getattr(request, "selection_count", 0)
            or defaults.default_top_n_holdings
        )
    else:
        top_n_holdings = profile.top_n_target or defaults.default_top_n_holdings

    explicit_candidate_pool = {"candidate_pool_size", "shortlist_size"} & set(request_fields)
    if explicit_candidate_pool:
        candidate_pool_size = int(
            getattr(request, "candidate_pool_size", 0)
            or getattr(request, "shortlist_size", 0)
            or defaults.default_candidate_pool_size
        )
    else:
        candidate_pool_size = profile.candidate_pool_size or defaults.default_candidate_pool_size

    explicit_weighting = {"weighting_mode", "weighting_method"} & set(request_fields)
    if explicit_weighting:
        weighting_mode = (
            getattr(request, "weighting_mode", "")
            or getattr(request, "weighting_method", "")
            or defaults.default_weighting_mode
        )
    else:
        weighting_mode = profile.weighting_mode or defaults.default_weighting_mode

    return PortfolioConstructionConfig(
        candidate_pool_size=max(top_n_holdings, candidate_pool_size),
        top_n_holdings=max(1, top_n_holdings),
        min_conviction_score=float(
            _request_value(request, "min_conviction_score", profile.min_conviction_score)
            if "min_conviction_score" in request_fields
            else (profile.min_conviction_score or defaults.default_min_conviction_score)
        ),
        min_confidence_threshold=float(
            _request_value(request, "min_confidence_threshold", user_settings.agents.min_confidence_threshold)
            if "min_confidence_threshold" in request_fields
            else user_settings.agents.min_confidence_threshold
        ),
        weighting_mode=weighting_mode,
        score_normalization_mode=(
            _request_value(request, "score_normalization_mode", defaults.default_score_normalization_mode)
        ),
        score_exponent=float(
            _request_value(request, "score_exponent", profile.score_exponent)
            if "score_exponent" in request_fields
            else (profile.score_exponent or defaults.default_score_exponent)
        ),
        risk_adjustment_mode=(
            _request_value(request, "risk_adjustment_mode", profile.risk_adjustment_mode)
            if "risk_adjustment_mode" in request_fields
            else (profile.risk_adjustment_mode or defaults.default_risk_adjustment_mode)
        ),
        min_position_pct=float(
            _request_value(request, "min_position_pct", profile.min_position_pct)
            if "min_position_pct" in request_fields
            else (profile.min_position_pct or defaults.default_min_position_pct)
        ),
        max_position_pct=float(
            _request_value(request, "max_position_pct", profile.max_position_pct)
            if "max_position_pct" in request_fields
            else (profile.max_position_pct or defaults.default_max_position_pct)
        ),
        cash_floor_pct=float(
            _request_value(request, "cash_floor_pct", profile.cash_floor_pct)
            if "cash_floor_pct" in request_fields
            else (profile.cash_floor_pct or defaults.default_cash_floor_pct)
        ),
        max_gross_exposure_pct=float(
            _request_value(request, "max_gross_exposure_pct", profile.max_gross_exposure_pct)
            if "max_gross_exposure_pct" in request_fields
            else (profile.max_gross_exposure_pct or defaults.default_max_gross_exposure_pct)
        ),
        sector_cap_pct=float(
            _request_value(request, "sector_cap_pct", profile.sector_cap_pct)
            if "sector_cap_pct" in request_fields
            else (profile.sector_cap_pct or defaults.default_sector_cap_pct)
        ),
        selection_buffer_pct=float(
            _request_value(request, "selection_buffer_pct", profile.selection_buffer_pct)
            if "selection_buffer_pct" in request_fields
            else (profile.selection_buffer_pct or defaults.default_selection_buffer_pct)
        ),
        turnover_buffer_pct=float(
            _request_value(request, "turnover_buffer_pct", profile.turnover_buffer_pct)
            if "turnover_buffer_pct" in request_fields
            else (profile.turnover_buffer_pct or defaults.default_turnover_buffer_pct)
        ),
        max_turnover_pct=float(
            _request_value(request, "max_turnover_pct", profile.max_turnover_pct)
            if "max_turnover_pct" in request_fields
            else (profile.max_turnover_pct or defaults.default_max_turnover_pct)
        ),
        hold_zone_pct=float(
            _request_value(request, "hold_zone_pct", profile.hold_zone_pct)
            if "hold_zone_pct" in request_fields
            else (profile.hold_zone_pct or defaults.default_hold_zone_pct)
        ),
        replacement_threshold=float(
            _request_value(request, "replacement_threshold", profile.replacement_threshold)
            if "replacement_threshold" in request_fields
            else (profile.replacement_threshold or defaults.default_replacement_threshold)
        ),
        persistence_bonus=float(
            _request_value(request, "persistence_bonus", profile.persistence_bonus)
            if "persistence_bonus" in request_fields
            else (profile.persistence_bonus or defaults.default_persistence_bonus)
        ),
        min_price=float(
            _request_value(request, "min_price", defaults.default_min_price)
        ),
        min_avg_dollar_volume_millions=float(
            _request_value(
                request,
                "min_avg_dollar_volume_millions",
                defaults.default_min_avg_dollar_volume_millions,
            )
        ),
        liquidity_lookback_days=int(
            _request_value(request, "liquidity_lookback_days", defaults.default_liquidity_lookback_days)
        ),
        min_history_days=int(
            _request_value(request, "min_history_days", defaults.default_min_history_days)
        ),
        rebalance_frequency_preference=profile.rebalance_frequency_preference,
        sector_exclusions=sorted(set(team.sector_exclusions)),
    )


def construct_target_weights(
    *,
    events: list[DecisionEvent],
    current_weights_pct: dict[str, float],
    volatility_by_ticker: dict[str, float],
    sectors: dict[str, str],
    config: PortfolioConstructionConfig,
) -> ConstructionPlan:
    if not events:
        return ConstructionPlan(
            weights={},
            target_gross_pct=0.0,
            target_cash_pct=100.0,
            average_priority_score=0.0,
            turnover_pct=0.0,
            selected_tickers=[],
            excluded_tickers=[],
            replaced_tickers=[],
            notes=["No candidate evaluations were available for portfolio construction."],
        )

    held_tickers = {ticker for ticker, weight in current_weights_pct.items() if weight > 0}
    selected_by_current: set[str] = set()
    candidates: list[dict[str, Any]] = []
    excluded_tickers: list[str] = []

    for event in events:
        event.current_weight_pct = round(current_weights_pct.get(event.ticker, 0.0), 2)
        details = {
            "direction_score": round(event.decision.direction_score, 4),
            "conviction_score": round(event.decision.conviction_score, 4),
            "priority_score": round(event.decision.priority_score, 4),
            "agreement_score": round(event.decision.agreement_score, 4),
            "coverage_score": round(event.decision.coverage_score, 4),
        }
        event.construction_details = details
        event.selection_reason = ""
        event.exclusion_reason = ""
        event.target_weight_pct = 0.0

        if event.ticker in held_tickers:
            selected_by_current.add(event.ticker)

        sector = sectors.get(event.ticker, "unknown")
        if config.sector_exclusions and sector in config.sector_exclusions:
            event.exclusion_reason = f"Excluded by team sector filter: {sector}."
            excluded_tickers.append(event.ticker)
            continue

        if event.decision.action != "BUY" or event.decision.direction_score <= 0:
            event.exclusion_reason = "Directional score was not positive enough to merit capital."
            excluded_tickers.append(event.ticker)
            continue
        if event.decision.priority_score < config.min_conviction_score:
            event.exclusion_reason = (
                f"Priority score {event.decision.priority_score:.2f} was below the "
                f"{config.min_conviction_score:.2f} conviction threshold."
            )
            excluded_tickers.append(event.ticker)
            continue
        if event.decision.confidence < config.min_confidence_threshold:
            event.exclusion_reason = (
                f"Confidence {event.decision.confidence:.2f} was below the "
                f"{config.min_confidence_threshold:.2f} minimum."
            )
            excluded_tickers.append(event.ticker)
            continue

        base_score = max(event.decision.priority_score, 0.0)
        adjusted_score = base_score + (
            config.persistence_bonus if event.ticker in held_tickers else 0.0
        )
        candidates.append(
            {
                "event": event,
                "base_score": base_score,
                "adjusted_score": adjusted_score,
                "held": event.ticker in held_tickers,
                "sector": sector,
            }
        )

    if not candidates:
        return ConstructionPlan(
            weights={},
            target_gross_pct=0.0,
            target_cash_pct=100.0,
            average_priority_score=0.0,
            turnover_pct=_turnover_pct(current_weights_pct, {}),
            selected_tickers=[],
            excluded_tickers=sorted(set(excluded_tickers)),
            replaced_tickers=sorted(selected_by_current),
            notes=["All names failed the conviction, confidence, or sector eligibility tests."],
        )

    candidates.sort(key=lambda item: item["base_score"], reverse=True)
    base_rank = {
        item["event"].ticker: rank + 1
        for rank, item in enumerate(candidates)
    }
    target_slots = min(config.top_n_holdings, len(candidates))
    retain_rank_cutoff = max(
        target_slots,
        int(ceil(target_slots * (1.0 + config.selection_buffer_pct))),
    )

    selected = sorted(candidates, key=lambda item: item["adjusted_score"], reverse=True)[:target_slots]
    selected_tickers = {item["event"].ticker for item in selected}

    # Buffer incumbents to reduce churn when new candidates barely beat them.
    for item in candidates:
        ticker = item["event"].ticker
        if not item["held"] or ticker in selected_tickers:
            continue
        if base_rank.get(ticker, retain_rank_cutoff + 1) > retain_rank_cutoff:
            continue
        challengers = [
            challenger
            for challenger in selected
            if not challenger["held"]
        ]
        if not challengers:
            continue
        weakest_new = min(challengers, key=lambda challenger: challenger["adjusted_score"])
        score_gap = weakest_new["adjusted_score"] - item["adjusted_score"]
        if score_gap < config.replacement_threshold:
            selected.remove(weakest_new)
            weakest_new["event"].exclusion_reason = (
                f"Replaced by held name buffer; score gap {score_gap:.2f} was below the "
                f"{config.replacement_threshold:.2f} replacement threshold."
            )
            selected.append(item)
            selected_tickers.remove(weakest_new["event"].ticker)
            selected_tickers.add(ticker)

    selected.sort(key=lambda item: item["adjusted_score"], reverse=True)
    average_priority_score = sum(item["base_score"] for item in selected) / max(1, len(selected))
    full_deploy_score = min(
        0.9,
        max(config.min_conviction_score + 0.25, config.min_confidence_threshold),
    )
    deployable_pct = max(0.0, config.max_gross_exposure_pct - config.cash_floor_pct)
    target_gross_pct = deployable_pct * _clamp(average_priority_score / max(full_deploy_score, 0.01), 0.0, 1.0)

    while selected and config.min_position_pct > 0 and target_gross_pct < len(selected) * config.min_position_pct:
        removed = selected.pop()
        removed["event"].exclusion_reason = (
            "Dropped because target gross exposure could not fund the configured minimum position size."
        )
        selected_tickers.remove(removed["event"].ticker)
        excluded_tickers.append(removed["event"].ticker)

    if not selected or target_gross_pct <= 0:
        return ConstructionPlan(
            weights={},
            target_gross_pct=0.0,
            target_cash_pct=100.0,
            average_priority_score=average_priority_score,
            turnover_pct=_turnover_pct(current_weights_pct, {}),
            selected_tickers=[],
            excluded_tickers=sorted(set(excluded_tickers)),
            replaced_tickers=sorted(held_tickers),
            notes=["The opportunity set was too weak to deploy capital after cash and min-position rules."],
        )

    raw_weights = [
        _raw_weight_signal(
            base_score=item["base_score"],
            confidence=item["event"].decision.confidence,
            volatility=volatility_by_ticker.get(item["event"].ticker, 0.25),
            weighting_mode=config.weighting_mode,
            normalization_mode=config.score_normalization_mode,
            exponent=config.score_exponent,
            risk_adjustment_mode=config.risk_adjustment_mode,
            conviction_floor=config.min_conviction_score,
        )
        for item in selected
    ]
    caps = [config.max_position_pct / 100.0 for _item in selected]
    weights = _allocate_with_floors(
        raw_weights=raw_weights,
        caps=caps,
        gross_target=target_gross_pct / 100.0,
        floor=config.min_position_pct / 100.0,
    )
    weights = _apply_sector_caps(
        weights=weights,
        tickers=[item["event"].ticker for item in selected],
        sectors=sectors,
        sector_cap=config.sector_cap_pct / 100.0,
    )

    target_weights = {
        item["event"].ticker: weight
        for item, weight in zip(selected, weights, strict=True)
        if weight > 1e-6
    }

    target_weights = _apply_turnover_controls(
        target_weights=target_weights,
        current_weights=current_weights_pct,
        config=config,
    )
    turnover_pct = _turnover_pct(current_weights_pct, target_weights)
    final_selected = [
        ticker
        for ticker, weight in sorted(target_weights.items(), key=lambda item: item[1], reverse=True)
        if weight > 0
    ]
    replaced_tickers = sorted(ticker for ticker in held_tickers if ticker not in final_selected)
    final_excluded = set(excluded_tickers)

    for item in candidates:
        event = item["event"]
        target_weight_pct = round(target_weights.get(event.ticker, 0.0) * 100.0, 2)
        event.target_weight_pct = target_weight_pct
        event.selected_for_execution = target_weight_pct > 0
        if event.selected_for_execution:
            if event.ticker in held_tickers and target_weight_pct >= event.current_weight_pct:
                event.selection_reason = (
                    f"Held and upsized from {event.current_weight_pct:.2f}% to {target_weight_pct:.2f}% "
                    "because conviction stayed strong."
                )
            elif event.ticker in held_tickers:
                event.selection_reason = (
                    f"Held through rebalance buffer at {target_weight_pct:.2f}% with persistence support."
                )
            else:
                rank = base_rank.get(event.ticker, 0)
                event.selection_reason = (
                    f"Selected at rank {rank} with priority {event.decision.priority_score:.2f} "
                    f"and target weight {target_weight_pct:.2f}%."
                )
        else:
            if not event.exclusion_reason:
                if event.ticker in replaced_tickers:
                    event.exclusion_reason = "Replaced by higher-ranked names at rebalance."
                else:
                    event.exclusion_reason = "Did not survive the rank/select/weight step."
            final_excluded.add(event.ticker)

    notes = [
        (
            f"Default constructor used {config.weighting_mode} weighting across up to "
            f"{config.top_n_holdings} holdings with a {config.max_position_pct:.1f}% single-name cap."
        ),
        (
            f"Target gross exposure resolved to {target_gross_pct:.1f}% from an average priority score "
            f"of {average_priority_score:.2f}."
        ),
    ]

    return ConstructionPlan(
        weights=target_weights,
        target_gross_pct=round(sum(target_weights.values()) * 100.0, 2),
        target_cash_pct=round(max(0.0, 100.0 - (sum(target_weights.values()) * 100.0)), 2),
        average_priority_score=round(average_priority_score, 4),
        turnover_pct=round(turnover_pct, 2),
        selected_tickers=final_selected,
        excluded_tickers=sorted(final_excluded),
        replaced_tickers=replaced_tickers,
        notes=notes,
    )


def _raw_weight_signal(
    *,
    base_score: float,
    confidence: float,
    volatility: float,
    weighting_mode: str,
    normalization_mode: str,
    exponent: float,
    risk_adjustment_mode: str,
    conviction_floor: float,
) -> float:
    normalized_score = _clamp(
        (base_score - conviction_floor) / max(1.0 - conviction_floor, 1e-6),
        0.01,
        1.0,
    )
    if weighting_mode == "equal_weight":
        raw = 1.0
    elif weighting_mode == "confidence_weighted":
        raw = max(confidence, 0.01)
    else:
        raw = normalized_score
        if normalization_mode == "power":
            raw = raw**max(1.0, exponent)
        raw *= max(confidence, 0.05)

    if weighting_mode == "risk_budgeted":
        risk_adjustment_mode = "full_inverse_vol"

    if risk_adjustment_mode == "mild_inverse_vol":
        raw *= 1.0 / sqrt(max(volatility, 0.12))
    elif risk_adjustment_mode == "full_inverse_vol":
        raw *= 1.0 / max(volatility, 0.12)
    return max(raw, 0.0001)


def _allocate_with_floors(
    *,
    raw_weights: list[float],
    caps: list[float],
    gross_target: float,
    floor: float,
) -> list[float]:
    if not raw_weights or gross_target <= 0:
        return [0.0 for _ in raw_weights]
    effective_floor = max(0.0, floor)
    if effective_floor * len(raw_weights) > gross_target:
        effective_floor = gross_target / len(raw_weights)
    weights = [effective_floor for _ in raw_weights]
    remaining = gross_target - sum(weights)
    if remaining <= 1e-9:
        return [min(weight, cap) for weight, cap in zip(weights, caps, strict=True)]

    extra_caps = [max(0.0, cap - effective_floor) for cap in caps]
    extras = _allocate_capped(raw_weights, extra_caps, remaining)
    return [
        min(base + extra, cap)
        for base, extra, cap in zip(weights, extras, caps, strict=True)
    ]


def _allocate_capped(raw_weights: list[float], caps: list[float], gross_target: float) -> list[float]:
    weights = [0.0 for _ in raw_weights]
    remaining = min(gross_target, sum(caps))
    active = [index for index, cap in enumerate(caps) if cap > 0]
    if remaining <= 0 or not active:
        return weights

    while active and remaining > 1e-9:
        active_total = sum(raw_weights[index] for index in active)
        if active_total <= 0:
            equal_share = remaining / len(active)
            for index in list(active):
                room = caps[index] - weights[index]
                allocation = min(equal_share, room)
                weights[index] += allocation
            break

        saturated: list[int] = []
        distributed = 0.0
        for index in active:
            room = max(0.0, caps[index] - weights[index])
            if room <= 1e-9:
                saturated.append(index)
                continue
            desired = remaining * (raw_weights[index] / active_total)
            allocation = min(desired, room)
            weights[index] += allocation
            distributed += allocation
            if room - allocation <= 1e-9:
                saturated.append(index)

        active = [index for index in active if index not in saturated]
        new_remaining = gross_target - sum(weights)
        if abs(new_remaining - remaining) <= 1e-9 or distributed <= 1e-9:
            break
        remaining = new_remaining

    return [max(0.0, min(weight, cap)) for weight, cap in zip(weights, caps, strict=True)]


def _apply_sector_caps(
    *,
    weights: list[float],
    tickers: list[str],
    sectors: dict[str, str],
    sector_cap: float,
) -> list[float]:
    if sector_cap <= 0:
        return weights
    adjusted = list(weights)
    totals: dict[str, float] = {}
    for ticker, weight in zip(tickers, adjusted, strict=True):
        sector = sectors.get(ticker, "unknown")
        totals[sector] = totals.get(sector, 0.0) + weight

    for sector, total in totals.items():
        if total <= sector_cap:
            continue
        scale = sector_cap / total
        for index, ticker in enumerate(tickers):
            if sectors.get(ticker, "unknown") == sector:
                adjusted[index] *= scale
    return adjusted


def _apply_turnover_controls(
    *,
    target_weights: dict[str, float],
    current_weights: dict[str, float],
    config: PortfolioConstructionConfig,
) -> dict[str, float]:
    adjusted = dict(target_weights)
    continuing = set(adjusted) & set(current_weights)
    for ticker in continuing:
        current = current_weights.get(ticker, 0.0) / 100.0
        target = adjusted.get(ticker, 0.0)
        buffered = current + ((target - current) * (1.0 - config.turnover_buffer_pct))
        adjusted[ticker] = buffered

    hold_zone = config.hold_zone_pct / 100.0
    all_tickers = set(adjusted) | set(current_weights)
    for ticker in all_tickers:
        current = current_weights.get(ticker, 0.0) / 100.0
        target = adjusted.get(ticker, 0.0)
        if abs(target - current) < hold_zone:
            adjusted[ticker] = current

    turnover_pct = _turnover_pct(current_weights, adjusted)
    if turnover_pct > config.max_turnover_pct and turnover_pct > 0:
        scale = config.max_turnover_pct / turnover_pct
        for ticker in list(all_tickers):
            current = current_weights.get(ticker, 0.0) / 100.0
            target = adjusted.get(ticker, 0.0)
            adjusted[ticker] = current + ((target - current) * scale)

    return {
        ticker: max(0.0, weight)
        for ticker, weight in adjusted.items()
        if weight > 1e-6
    }


def _turnover_pct(current_weights: dict[str, float], target_weights: dict[str, float]) -> float:
    all_tickers = set(current_weights) | set(target_weights)
    one_way_turnover = 0.0
    for ticker in all_tickers:
        current = current_weights.get(ticker, 0.0) / 100.0
        target = target_weights.get(ticker, 0.0)
        one_way_turnover += abs(target - current)
    return round(one_way_turnover * 50.0, 4)


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _request_value(request: Any, field_name: str, fallback: Any) -> Any:
    value = getattr(request, field_name, None)
    return fallback if value is None else value
