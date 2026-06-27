import re

WEEKDAYS = {
    "monday": 1, "tuesday": 2, "wednesday": 3, "thursday": 4,
    "friday": 5, "saturday": 6, "sunday": 7,
    "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7
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

def search_flight_schedules(origin: str, dest: str, date: str) -> dict:
    """Mock database lookup for flight schedules. Returns available flights."""
    origin = origin.upper().strip()
    dest = dest.upper().strip()
    date = date.lower().strip()
    
    # Mock data
    MOCK_DB = {
        ("SEA", "SFO"): [
            {"carrier": "DL", "flight_no": "1234", "dep_time": "08:30am", "origin": "SEA"},
            {"carrier": "AS", "flight_no": "5678", "dep_time": "01:00pm", "origin": "SEA"},
            {"carrier": "UA", "flight_no": "9012", "dep_time": "06:45pm", "origin": "SEA"}
        ],
        ("PAE", "SFO"): [
            {"carrier": "AS", "flight_no": "1111", "dep_time": "07:00am", "origin": "PAE"},
        ]
    }
    
    flights = MOCK_DB.get((origin, dest), [])
    
    if not flights:
        return {"status": "no_flights_found", "message": f"No flights found from {origin} to {dest} on {date}."}
        
    return {"status": "success", "flights": flights}
