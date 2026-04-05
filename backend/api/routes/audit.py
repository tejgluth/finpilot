from __future__ import annotations

import aiosqlite
import json
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from backend.config import settings


router = APIRouter()


@router.get("/")
async def list_audit_events(limit: int = 100):
    async with aiosqlite.connect(settings.db_path) as db:
        async with db.execute(
            "SELECT timestamp, actor, event_type, data FROM audit_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
    entries = []
    for row in rows:
        try:
            parsed = json.loads(row[3])
        except json.JSONDecodeError:
            parsed = {
                "timestamp": row[0],
                "actor": row[1],
                "event_type": row[2],
                "details": row[3],
            }
        entries.append(parsed)
    return {"entries": entries}


@router.get("/export", response_class=PlainTextResponse)
async def export_audit_log():
    try:
        return settings.audit_log_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
