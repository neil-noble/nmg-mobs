import json
import re
from datetime import date, datetime

import config as C
import dashboard
import render
from model import assess, build_people
from tests.test_model import comp, flight, full_set, room

TODAY = date(2026, 10, 24)
NOW = datetime(2026, 10, 24, 6, 0, tzinfo=C.AWST)


def _report():
    rows = full_set("1") + full_set("2", first="Bo", last="O'NEIL </script><b>", email="2@x.au")
    rows[2] = comp("1", "National Police Clearance", "No document added")
    rows += [comp("3", "Other", "Does not expire", role="", first="Cy", last="NOROLE", email="3@x.au")]
    flights = [flight("Ann", "SMITH", "2026-10-26", "1@x.au"),
               flight("Bo", "O'NEIL </script><b>", "2026-10-27", "2@x.au"),
               flight("Zed", "UNKNOWN", "2026-10-28", "z@x.au")]
    return assess(build_people(rows), flights, [room("3", "2026-10-25")], TODAY)


def _embedded(page):
    raw = re.search(r'<script id="mobs-data" type="application/json">(.*?)</script>', page, re.S).group(1)
    return json.loads(raw)


def test_dashboard_data_carries_every_section():
    d = dashboard.data(_report())
    by_name = {p["n"]: p for p in d["people"]}
    assert by_name["SMITH, Ann"]["s"] == "n"
    assert by_name["SMITH, Ann"]["st"] == ["ok", "ok", "missing", "ok", "ok"]
    assert by_name["NOROLE, Cy"]["s"] == "r" and by_name["NOROLE, Cy"]["st"] is None
    assert by_name["UNKNOWN, Zed"]["s"] == "u"
    assert d["items"] == list(C.ITEMS)
    assert d["days"][0] == "2026-10-24" and len(d["days"]) == C.LOOKAHEAD_DAYS


def test_names_cannot_break_out_of_the_data_block():
    page = dashboard.page(_report(), NOW)
    raw = re.search(r'<script id="mobs-data" type="application/json">(.*?)</script>', page, re.S).group(1)
    assert "<" not in raw
    names = {p["n"] for p in _embedded(page)["people"]}
    assert "O'NEIL </SCRIPT><B>, Bo" in names        # round-trips intact once parsed


def test_empty_report_renders():
    page = dashboard.page(assess({}, [], [], TODAY), NOW)
    assert _embedded(page)["people"] == []


def test_email_subject_and_body():
    report = _report()
    assert render.email_subject(report, TODAY) == "Mobilisation compliance - 1 booked person not cleared - 24 Oct 2026"
    html, text = render.email_html(report), render.email_text(report)
    assert "SMITH, Ann" in html and C.DASHBOARD_URL in html
    assert "Police Clearance (missing)" in text
