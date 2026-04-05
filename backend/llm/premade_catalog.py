from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from backend.models.agent_team import PremadeTeamCatalog, PremadeTeamTemplate

_CATALOG_PATH = Path(__file__).parent / "premade_teams.yaml"


@lru_cache(maxsize=1)
def get_catalog() -> PremadeTeamCatalog:
    """Load and validate the premade team catalog from YAML. Cached after first load."""
    raw = yaml.safe_load(_CATALOG_PATH.read_text(encoding="utf-8"))
    return PremadeTeamCatalog.model_validate(raw)


def get_premade_team(team_id: str) -> PremadeTeamTemplate | None:
    return next((t for t in get_catalog().teams if t.team_id == team_id), None)


def get_default_template() -> PremadeTeamTemplate:
    catalog = get_catalog()
    return next(t for t in catalog.teams if t.is_default)


def get_featured_templates() -> list[PremadeTeamTemplate]:
    catalog = get_catalog()
    order = catalog.featured_team_ids
    by_id = {t.team_id: t for t in catalog.teams}
    return [by_id[tid] for tid in order if tid in by_id]


def reload_catalog() -> PremadeTeamCatalog:
    """Force a fresh load — used in tests when the YAML path is monkeypatched."""
    get_catalog.cache_clear()
    return get_catalog()
