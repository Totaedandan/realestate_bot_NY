from __future__ import annotations

import re
from typing import Optional


MONTHS_RU = {
    "янв": "January",
    "фев": "February",
    "мар": "March",
    "апр": "April",
    "мая": "May",
    "май": "May",
    "июн": "June",
    "июл": "July",
    "авг": "August",
    "сен": "September",
    "окт": "October",
    "ноя": "November",
    "дек": "December",
}

_WORD_TO_NUM = {"двое": 2, "трое": 3, "четверо": 4, "пятеро": 5, "шестеро": 6}


def extract_people_count(text: str) -> Optional[int]:
    if not text:
        return None
    tl = text.lower().strip()

    m = re.search(r"\bнас\s+(двое|трое|четверо|пятеро|шестеро)\b", tl)
    if m:
        return _WORD_TO_NUM[m.group(1)]

    m = re.search(r"\bнас\s*[:\-]?\s*(\d{1,2})\b", tl)
    if m:
        return int(m.group(1))

    m = re.search(r"\b(\d{1,2})\s*(чел|человек|people|persons)\b", tl)
    if m:
        return int(m.group(1))

    m = re.search(r"(people|persons)\s*[:\-]?\s*(\d{1,2})", tl)
    if m:
        return int(m.group(2))

    if "вдвоем" in tl or "вдвоём" in tl:
        return 2

    if any(x in tl for x in ["я одна", "только я", "just me", "only me"]):
        return 1

    return None


def extract_move_in(text: str) -> Optional[str]:
    if not text:
        return None
    tl = text.lower().strip()
    if not tl:
        return None

    if any(x in tl for x in ["на днях", "в ближайшие дни", "в ближайшее время", "скоро", "soon", "next few days"]):
        return "в ближайшие дни"

    if any(x in tl for x in ["asap", "срочно", "как можно скорее", "сразу"]):
        return "ASAP"
    if "сегодня" in tl or "today" in tl:
        return "today"
    if "завтра" in tl or "tomorrow" in tl:
        return "tomorrow"

    m = re.search(r"через\s*(\d{1,2})\s*(дн|дня|дней|нед|недел|мес|месяц|месяца|месяцев)", tl)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        if unit.startswith("д"):
            return f"через {n} дней"
        if unit.startswith("н"):
            return f"через {n} недель"
        return f"через {n} месяцев"

    m = re.search(r"\bin\s*(\d{1,2})\s*(day|days|week|weeks|month|months)\b", tl)
    if m:
        return f"in {int(m.group(1))} {m.group(2)}"

    m = re.search(
        r"\b(\d{1,2})\s*(январ\w*|феврал\w*|март\w*|апрел\w*|ма\w*|июн\w*|июл\w*|август\w*|сентябр\w*|октябр\w*|ноябр\w*|декабр\w*)",
        tl,
    )
    if m:
        day = m.group(1)
        mon_key = m.group(2)[:3]
        month = MONTHS_RU.get(mon_key, m.group(2))
        return f"{day} {month}"

    return None


def extract_showing_time(text: str) -> Optional[str]:
    """
    Return a compact normalized string for manager:
    - "today 7pm"
    - "today after 8pm"
    - "tomorrow 19:00"
    Also supports RU "в 7 вечера", "после 8", "после 20:00"
    """
    if not text:
        return None
    tl = text.lower().strip()
    if not tl:
        return None

    day = None
    if "сегодня" in tl or "today" in tl:
        day = "today"
    elif "завтра" in tl or "tomorrow" in tl:
        day = "tomorrow"

    # capture time like 19:00 / 7:30
    m = re.search(r"\b(\d{1,2})[:\.](\d{2})\b", tl)
    if m:
        hh = int(m.group(1))
        mm = m.group(2)
        prefix = "after " if any(w in tl for w in ["после", "after"]) else ""
        if day:
            return f"{day} {prefix}{hh:02d}:{mm}"
        return f"{prefix}{hh:02d}:{mm}".strip()

    # capture "в 7", "в 7 вечера", "at 7", "7 pm"
    m = re.search(r"\b(\d{1,2})\b", tl)
    if m:
        hh = int(m.group(1))
        is_after = any(w in tl for w in ["после", "after"])
        is_pm = any(w in tl for w in ["вечера", "pm", "p.m"])
        # If "вечера" and hour is 1..11 -> convert to 13..23
        if is_pm and 1 <= hh <= 11:
            hh += 12
        prefix = "after " if is_after else ""
        if day:
            return f"{day} {prefix}{hh:02d}:00".strip()
        return f"{prefix}{hh:02d}:00".strip()

    # just day
    if day:
        return day

    return None
