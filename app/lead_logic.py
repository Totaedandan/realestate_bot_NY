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
    if pc and not lead.people_count:
        lead.people_count = pc

    mv = extract_move_in(t)
    if mv and not lead.move_in:
        lead.move_in = mv

    last_q = (lead.last_question or "").lower()

    # Employment: if we asked about work — accept any non-empty answer
    if not lead.employment and ("кем" in last_q or "работ" in last_q):
        lead.employment = t[:160]

    # Showing: if we asked about showing — store raw and parse
    if "показ" in last_q:
        if not lead.showing_text:
            lead.showing_text = t[:200]
        if not lead.showing_time:
            st = extract_showing_time(t)
            if st:
                lead.showing_time = st


def next_question(lead: LeadState) -> Tuple[str, Optional[str], bool]:
    if lead.handoff_sent:
        return (FINAL, None, False)

    if not lead.people_count or not lead.move_in:
        return (Q1, Q1, False)

    if not lead.employment:
        return (Q2, Q2, False)

    if not lead.showing_time and not lead.showing_text:
        return (Q3, Q3, False)

    return (FINAL, None, True)


def decide_reply(lead: LeadState, user_text: str) -> Tuple[str, Optional[str], bool, bool]:
    before = (lead.people_count, lead.move_in, lead.employment, lead.showing_time, lead.showing_text)

    apply_extraction(lead, user_text)

    after = (lead.people_count, lead.move_in, lead.employment, lead.showing_time, lead.showing_text)
    progressed = before != after

    # stuck counter: no "не понял" on first fail
    if progressed:
        lead.stuck_count = 0
    else:
        lead.stuck_count = (lead.stuck_count or 0) + 1

    reply, next_q, do_handoff = next_question(lead)

    if not progressed and lead.last_question and not lead.handoff_sent and lead.stuck_count >= 2:
        reply = "Не совсем понял. " + reply

    if next_q:
        lead.last_question = next_q

    return reply, next_q, do_handoff, False
