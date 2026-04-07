from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
import json

from backend.config import settings
from backend.models.agent_team import ExecutionSnapshot
from backend.models.backtest_result import BacktestArtifact


def write_artifact(
    config_snapshot: dict,
    transaction_cost_model: dict,
    portfolio_construction: dict,
    metrics: dict,
    execution_snapshot: ExecutionSnapshot,
    temporal_features: dict,
    supplemental_payload: dict | None = None,
) -> BacktestArtifact:
    created_at = datetime.now(UTC).isoformat()
    # Extract custom reasoning specs + team classification for audit
    effective_team = execution_snapshot.effective_team
    compiled_reasoning_specs = {
        node_id: spec.model_dump(mode="json")
        for node_id, spec in (effective_team.compiled_reasoning_specs or {}).items()
    }
    team_meta = {
        "team_classification": getattr(effective_team, "team_classification", "premade"),
        "topology_hash": getattr(effective_team, "topology_hash", ""),
        "prompt_override_present": getattr(effective_team, "prompt_override_present", False),
        "compiled_reasoning_specs": compiled_reasoning_specs,
    }

    artifact_payload = {
        "config_snapshot": config_snapshot,
        "transaction_cost_model": transaction_cost_model,
        "portfolio_construction": portfolio_construction,
        "metrics": metrics,
        "execution_snapshot": execution_snapshot.model_dump(mode="json"),
        "temporal_features": temporal_features,
        "supplemental_payload": supplemental_payload or {},
        "team_meta": team_meta,
    }
    raw_hash = sha256(json.dumps(artifact_payload, sort_keys=True).encode("utf-8")).hexdigest()
    artifact_id = raw_hash[:8]
    artifact = {
        "artifact_id": artifact_id,
        "data_hash": raw_hash,
        "config_snapshot": config_snapshot,
        "transaction_cost_model": transaction_cost_model,
        "portfolio_construction": portfolio_construction,
        "created_at": created_at,
        "benchmark_symbol": "SPY",
        "metrics": metrics,
        "execution_snapshot": execution_snapshot.model_dump(mode="json"),
        "temporal_features": temporal_features,
        "supplemental_payload": supplemental_payload or {},
        "team_meta": team_meta,
    }
    Path(settings.artifacts_dir).mkdir(parents=True, exist_ok=True)
    path = Path(settings.artifacts_dir) / f"{artifact_id}.json"
    path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    return BacktestArtifact(
        artifact_id=artifact_id,
        data_hash=raw_hash,
        config_snapshot=config_snapshot,
        transaction_cost_model=transaction_cost_model,
        portfolio_construction=portfolio_construction,
        created_at=created_at,
        benchmark_symbol="SPY",
        artifact_path=str(path),
        execution_snapshot=execution_snapshot,
        temporal_features=temporal_features,
    )
