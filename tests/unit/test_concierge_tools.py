import pytest
from agents.concierge_tools import resolve_flight_query

def test_resolve_flight_query_12h_pm():
    res = resolve_flight_query("DL", "ORD", "ATL", "Monday", "7pm")
    assert res["day_of_week"] == 1
    assert res["dep_time_blk"] == "1900-1959"
    assert res["carrier"] == "DL"
    assert res["origin"] == "ORD"
    assert res["dest"] == "ATL"

def test_resolve_flight_query_24h_leading_zero():
    res = resolve_flight_query("AA", "JFK", "LAX", "Tuesday", "07:00")
    assert res["day_of_week"] == 2
    assert res["dep_time_blk"] == "0700-0759"

def test_resolve_flight_query_midnight_lump():
    res = resolve_flight_query("UA", "SFO", "DEN", "Sun", "00:30")
    assert res["day_of_week"] == 7
    assert res["dep_time_blk"] == "0001-0559"

def test_resolve_flight_query_noon():
    res = resolve_flight_query("DL", "SEA", "JFK", "Wed", "12:00pm")
    assert res["day_of_week"] == 3
    assert res["dep_time_blk"] == "1200-1259"
    
def test_resolve_flight_query_midnight_am():
    res = resolve_flight_query("DL", "SEA", "JFK", "Wed", "12:00am")
    assert res["dep_time_blk"] == "0001-0559"
