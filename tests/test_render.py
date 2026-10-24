from datetime import date, datetime

import config as C
import render
from model import assess, build_people
from tests.test_model import comp, flight, full_set, room

TODAY = date(2026, 10, 24)


def _report():
    rows = full_set("1") + full_set("2", first="Bo", last="O'NEIL <b>", email="2@x.au")
    rows[2] = comp("1", "National Police Clearance", "No document added")
    rows += [comp("3", "Other", "Does not expire", role="", first="Cy", last="NOROLE", email="3@x.au")]
    flights = [flight("Ann", "SMITH", "2026-10-26", "1@x.au"), flight("Bo", "O'NEIL <b>", "2026-10-27", "2@x.au"),
               flight("Zed", "UNKNOWN", "2026-10-28", "z@x.au")]
    return assess(build_people(rows), flights, [room("3", "2026-10-25")], TODAY)


def test_dashboard_lists_each_section_and_escapes_names():
    page = render.dashboard(_report(), datetime(2026, 10, 24, 6, 0, tzinfo=C.AWST))
    assert "SMITH, Ann" in page and "NOROLE, Cy" in page and "UNKNOWN, Zed" in page
    assert "O&#x27;NEIL &lt;B&gt;" in page and "<B>" not in page
    assert page.count('class="pill missing"') == 1
    assert "Cleared to mobilise (1)" in page


def test_email_subject_and_body():
    report = _report()
    assert render.email_subject(report, TODAY) == "Mobilisation compliance - 1 booked person not cleared - 24 Oct 2026"
    html, text = render.email_html(report), render.email_text(report)
    assert "SMITH, Ann" in html and C.DASHBOARD_URL in html
    assert "Police Clearance (missing)" in text


def test_empty_report_renders():
    report = assess({}, [], [], TODAY)
    page = render.dashboard(report, datetime(2026, 10, 24, 6, 0, tzinfo=C.AWST))
    assert "Everyone booked with a work role has all five items." in page
