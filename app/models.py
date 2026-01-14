from __future__ import annotations

from dataclasses import dataclass, asdict, fields
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class LeadState:
    chat_id: int
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None

    people_count: Optional[int] = None
    move_in: Optional[str] = None
    employment: Optional[str] = None

    # Parsed "bucket" for showing (today/tomorrow), but ALSO keep raw text
    showing_time: Optional[str] = None
    showing_text: Optional[str] = None

    handoff_sent: bool = False
    paused: bool = False
    last_question: Optional[str] = None

    stuck_count: int = 0

    created_at: str = ""
    updated_at: str = ""

    def touch(self) -> None:
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        if not self.created_at:
            self.created_at = now
        self.updated_at = now

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "LeadState":
        allowed = {f.name for f in fields(LeadState)}
        cleaned = {k: v for k, v in (d or {}).items() if k in allowed}
        return LeadState(**cleaned)
