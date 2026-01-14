from __future__ import annotations
import os
import json
import aiosqlite
from typing import Optional
from app.config import settings
from app.models import LeadState

_DB: Optional[aiosqlite.Connection] = None

async def get_db() -> aiosqlite.Connection:
    global _DB
    if _DB is None:
        os.makedirs(os.path.dirname(settings.SQLITE_PATH), exist_ok=True)
        _DB = await aiosqlite.connect(settings.SQLITE_PATH)
        _DB.row_factory = aiosqlite.Row
    return _DB

async def init_db() -> None:
    db = await get_db()
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS leads (
            chat_id INTEGER PRIMARY KEY,
            data TEXT NOT NULL
        );
        """
    )
    await db.commit()

async def load_lead(chat_id: int) -> Optional[LeadState]:
    db = await get_db()
    cur = await db.execute("SELECT data FROM leads WHERE chat_id = ?", (chat_id,))
    row = await cur.fetchone()
    await cur.close()
    if not row:
        return None
    data = json.loads(row["data"])
    return LeadState.from_dict(data)

async def save_lead(lead: LeadState) -> None:
    db = await get_db()
    lead.touch()
    data = json.dumps(lead.to_dict(), ensure_ascii=False)
    await db.execute(
        """
        INSERT INTO leads(chat_id, data)
        VALUES(?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET data=excluded.data
        """,
        (lead.chat_id, data),
    )
    await db.commit()

async def reset_lead(chat_id: int) -> None:
    db = await get_db()
    await db.execute("DELETE FROM leads WHERE chat_id = ?", (chat_id,))
    await db.commit()
