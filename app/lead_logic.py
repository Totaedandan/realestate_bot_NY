from __future__ import annotations

from typing import Optional, Tuple

from app.models import LeadState
from app.utils import extract_move_in, extract_people_count, extract_showing_time

Q1 = "Здравствуйте, подскажите пожалуйста, сколько вас человек и когда примерно планируете заселение?"
Q2 = "Спасибо! Кем вы работаете ?"
Q3 = "Когда удобно подъехать на показ — сегодня или завтра? "
FINAL = "Понял. Менеджер уже получил ваш запрос и свяжется с вами."


def _clean_text(t: str) -> str:
    return (t or "").strip()


def apply_extraction(lead: LeadState, text: str) -> None:
    t = _clean_text(text)
    if not t:
        return

    pc = extract_people_count(t)
    if pc and not getattr(lead, "people_count", None):
        lead.people_count = pc

    mv = extract_move_in(t)
    if mv and not getattr(lead, "move_in", None):
        lead.move_in = mv

    last_q = (getattr(lead, "last_question", "") or "").lower()

    # Employment: if we asked about work — accept any non-empty answer
    if not getattr(lead, "employment", None) and ("кем" in last_q or "работ" in last_q):
        lead.employment = t[:160]

    # Showing: if we asked about showing — store raw and parse
    if "показ" in last_q:
        if not getattr(lead, "showing_text", None):
            lead.showing_text = t[:200]
        if not getattr(lead, "showing_time", None):
            st = extract_showing_time(t)
            if st:
                lead.showing_time = st


def next_question(lead: LeadState) -> Tuple[str, Optional[str], bool]:
    if getattr(lead, "handoff_sent", False):
        return (FINAL, None, False)

    if not getattr(lead, "people_count", None) or not getattr(lead, "move_in", None):
        return (Q1, Q1, False)

    if not getattr(lead, "employment", None):
        return (Q2, Q2, False)

    if not getattr(lead, "showing_time", None) and not getattr(lead, "showing_text", None):
        return (Q3, Q3, False)

    return (FINAL, None, True)


def decide_reply(lead: LeadState, user_text: str) -> Tuple[str, Optional[str], bool, bool]:
    before = (
        getattr(lead, "people_count", None),
        getattr(lead, "move_in", None),
        getattr(lead, "employment", None),
        getattr(lead, "showing_time", None),
        getattr(lead, "showing_text", None),
    )

    apply_extraction(lead, user_text)

    after = (
        getattr(lead, "people_count", None),
        getattr(lead, "move_in", None),
        getattr(lead, "employment", None),
        getattr(lead, "showing_time", None),
        getattr(lead, "showing_text", None),
    )
    progressed = before != after

    # stuck counter: no "не понял" on first fail
    stuck = getattr(lead, "stuck_count", 0) or 0
    if progressed:
        stuck = 0
    else:
        stuck += 1
    setattr(lead, "stuck_count", stuck)

    reply, next_q, do_handoff = next_question(lead)

    if not progressed and getattr(lead, "last_question", None) and not getattr(lead, "handoff_sent", False) and stuck >= 2:
        reply = "Не совсем понял. " + reply

    if next_q:
        lead.last_question = next_q

    return reply, next_q, do_handoff, False
