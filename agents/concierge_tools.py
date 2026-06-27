import re
from datetime import date, timedelta

WEEKDAYS = {
    "monday": 1, "tuesday": 2, "wednesday": 3, "thursday": 4,
    "friday": 5, "saturday": 6, "sunday": 7,
    "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7
}

_WD_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def resolve_date(expression: str, today: str | None = None) -> dict:
    """Resolve a relative or absolute date to an exact calendar date, anchored on the REAL
    current date. The LLM does not know today's date, so always use this for any date.

    Handles: 'today', 'tomorrow', 'day after tomorrow', a weekday ('friday'),
    'next <weekday>', and ISO dates ('2026-06-27').
    `today` (ISO yyyy-mm-dd) is for testing only; defaults to the real system date.
    """
    base = date.fromisoformat(today) if today else date.today()
    e = expression.strip().lower()
    target = None

    if e == "today":
        target = base
    elif e in ("tomorrow", "tmrw"):
        target = base + timedelta(days=1)
    elif e in ("day after tomorrow", "overmorrow"):
        target = base + timedelta(days=2)
    else:
        is_next = e.startswith("next ")
        name = e.replace("next ", "").replace("this ", "").replace("coming ", "").strip()
        if name in WEEKDAYS:
            delta = (WEEKDAYS[name] - base.isoweekday()) % 7
            if delta == 0:
                delta = 7 if is_next else 0
            target = base + timedelta(days=delta)
        else:
            try:
                target = date.fromisoformat(expression.strip())
            except ValueError:
                target = None

    if target is None:
        return {"status": "unparsed",
                "message": f"Could not resolve date '{expression}'.",
                "today": base.isoformat()}

    return {
        "status": "ok",
        "date": target.isoformat(),
        "weekday": _WD_NAMES[target.weekday()],
        "day_of_week": target.isoweekday(),   # 1=Mon ... 7=Sun
        "pretty": target.strftime("%A, %B %d, %Y").replace(" 0", " "),
    }

def _dep_time_blk(hhmm: int) -> str:
    """Map 24h HHMM -> BTS departure block. NOTE: first block lumps 00:01-05:59."""
    if hhmm < 600:
        return "0001-0559"
    h = hhmm // 100
    return f"{h:02d}00-{h:02d}59"   # 0600-0659 ... 2300-2359

def resolve_flight_query(carrier: str, origin: str, dest: str,
                         weekday: str, time_str: str) -> dict:
    """Deterministically normalize query parts into FlightContext fields.
    Handles 12h ('7pm','7:00 pm') and 24h ('0700','19:00') time_str."""
    time_str = time_str.lower().strip().replace(" ", "")
    match = re.match(r"^(\d{1,2}):?(\d{2})?(am|pm)?$", time_str)
    
    if match:
        hour_str, minute_str, am_pm = match.groups()
        hour = int(hour_str)
        minute = int(minute_str) if minute_str else 0
        
        if am_pm:
            if am_pm == "pm" and hour != 12:
                hour += 12
            elif am_pm == "am" and hour == 12:
                hour = 0
        
        hhmm = hour * 100 + minute
    else:
        # Fallback to noon if completely unparseable
        hhmm = 1200
        
    day_of_week = WEEKDAYS.get(weekday.strip().lower(), 1)

    return {
        "carrier": carrier.upper(),
        "origin": origin.upper(),
        "dest": dest.upper(),
        "day_of_week": day_of_week,
        "dep_time_blk": _dep_time_blk(hhmm)
    }
