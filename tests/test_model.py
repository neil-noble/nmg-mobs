from datetime import date

import config as C
from model import assess, build_people, row_state

TODAY = date(2026, 10, 24)


def comp(eid, name, status, role="*Permanent / Long Term Worker", **kw):
    row = {"employeeId": eid, "firstName": kw.get("first", "Ann"), "lastName": kw.get("last", "SMITH"),
           "employer": kw.get("employer", "NMG"), "workgroup": "CPO", "workEmail": kw.get("email", f"{eid}@x.au"),
           "workRole": role, "complianceName": name, "complianceStatus": status,
           "competencyName": None, "competencyStatus": None, "competencyDocumentUploaded": False}
    return row


def induction(eid, status, uploaded, role="*Permanent / Long Term Worker", **kw):
    row = comp(eid, None, None, role, **kw)
    row.update(competencyName="Crown Prince Project Site Induction", competencyStatus=status,
               competencyDocumentUploaded=uploaded)
    return row


def full_set(eid, role="*Permanent / Long Term Worker", medical="Pre Employment Medical", **kw):
    return [comp(eid, medical, "Does not expire", role, **kw),
            comp(eid, "Drug and Alcohol Screen", "Expiry on 01-Jan-2027", role, **kw),
            comp(eid, "National Police Clearance", "Does not expire", role, **kw),
            comp(eid, "Drivers License - C (Car)", "Expiring on 30-Oct-2026", role, **kw),
            induction(eid, "Competent", True, role, **kw)]


def flight(first, last, day, email="", **kw):
    return {"flightDate": f"{day}T00:00:00", "firstName": first, "lastName": last, "workEmail": email,
            "employer": "NMG", "departurePort": "Perth", "arrivalPort": "Meekathara",
            "bookingStatus": kw.get("status", "Booked"), "cancel": kw.get("cancel", False)}


def room(eid, day, camp="Westgold Camp"):
    return {"dateOfBooking": f"{day}T00:00:00", "employeeId": eid, "roomCamp": camp,
            "personFirstName": "X", "personLastName": "Y", "employer": "NMG"}


def test_row_states():
    assert row_state(comp("1", "X", "No document added")) == C.MISSING
    assert row_state(comp("1", "X", "Expired on 01-Jan-2026")) == C.EXPIRED
    assert row_state(comp("1", "X", "Expiring on 01-Nov-2026")) == C.OK
    assert row_state(comp("1", "X", "Something new")) == C.MISSING      # unknown never reads as cleared
    assert row_state(induction("1", "Competent", True)) == C.OK
    assert row_state(induction("1", "Competent", False)) == C.NO_DOCUMENT
    assert row_state(induction("1", "WR Requirement", False)) == C.MISSING
    assert row_state(induction("1", "Expired", True)) == C.EXPIRED


def test_complete_person_is_cleared():
    people = build_people(full_set("1"))
    report = assess(people, [flight("Ann", "SMITH", "2026-10-26", "1@x.au")], [], TODAY)
    assert [b.person.employee_id for b in report.cleared] == ["1"]
    assert report.not_cleared == []


def test_missing_item_is_flagged():
    rows = full_set("1")
    rows[2] = comp("1", "National Police Clearance", "No document added")
    report = assess(build_people(rows), [flight("Ann", "SMITH", "2026-10-26", "1@x.au")], [], TODAY)
    assert report.not_cleared[0].person.gaps() == {C.POLICE: C.MISSING}
    assert report.gap_counts()[C.POLICE] == 1


def test_best_row_wins_across_work_roles():
    rows = full_set("1") + [comp("1", "National Police Clearance", "No document added", "ERT Member")]
    assert build_people(rows)["1"].gaps() == {}


def test_item_absent_from_work_role_is_a_gap():
    rows = [r for r in full_set("1") if r["complianceName"] != "Drivers License - C (Car)"]
    assert build_people(rows)["1"].gaps() == {C.LICENCE: C.NOT_ON_ROLE}


def test_stw_medical_declaration_satisfies_medical():
    people = build_people(full_set("1", role="*Short Term Worker (STW)", medical="Medical Declaration"))
    assert people["1"].gaps() == {}


def test_medical_declaration_does_not_satisfy_long_term_worker():
    people = build_people(full_set("1", medical="Medical Declaration"))
    assert people["1"].gaps() == {C.MEDICAL: C.NOT_ON_ROLE}


def test_no_work_role_listed_separately():
    rows = [comp("1", "Some Other Thing", "Does not expire", role="")]
    report = assess(build_people(rows), [], [room("1", "2026-10-25")], TODAY)
    assert [b.person.employee_id for b in report.no_role] == ["1"]
    assert report.not_cleared == [] and report.cleared == []


def test_window_and_cancellations():
    people = build_people(full_set("1"))
    flights = [flight("Ann", "SMITH", "2026-10-23", "1@x.au"),                 # yesterday
               flight("Ann", "SMITH", "2026-11-07", "1@x.au"),                 # day 15 - outside
               flight("Ann", "SMITH", "2026-10-30", "1@x.au", cancel=True),
               flight("Ann", "SMITH", "2026-10-30", "1@x.au", status="Cancelled")]
    assert assess(people, flights, [], TODAY).booked_count == 0
    assert assess(people, [flight("Ann", "SMITH", "2026-11-06", "1@x.au")], [], TODAY).booked_count == 1


def test_flight_matched_by_unique_name_when_email_differs():
    people = build_people(full_set("1"))
    report = assess(people, [flight("ann", "Smith", "2026-10-26", "personal@gmail.com")], [], TODAY)
    assert len(report.cleared) == 1


def test_ambiguous_name_is_unmatched():
    rows = full_set("1") + full_set("2")
    report = assess(build_people(rows), [flight("Ann", "SMITH", "2026-10-26", "nobody@x.au")], [], TODAY)
    assert [u.name for u in report.unmatched] == ["SMITH, Ann"]


def test_room_nights_collapse_to_first_night():
    people = build_people(full_set("1"))
    rooms = [room("1", "2026-10-26"), room("1", "2026-10-25"), room("1", "2026-10-27")]
    booked = assess(people, [], rooms, TODAY).cleared[0]
    assert len(booked.bookings) == 1
    assert booked.first.day == date(2026, 10, 25)
    assert booked.first.detail == "Westgold Camp, 3 night(s)"


def test_by_employer_counts():
    rows = full_set("1", employer="A") + full_set("2", employer="B", first="Bo", last="JONES", email="2@x.au")
    rows[2] = comp("1", "National Police Clearance", "No document added", employer="A")
    flights = [flight("Ann", "SMITH", "2026-10-26", "1@x.au"), flight("Bo", "JONES", "2026-10-26", "2@x.au")]
    assert assess(build_people(rows), flights, [], TODAY).by_employer() == [("A", 1, 1), ("B", 1, 0)]


def test_excluded_employers_leave_only_their_section():
    nmg = dict(employer="new murchison gold ltd")                      # case does not matter
    rows = (full_set("1", **nmg)                                        # NMG, cleared: still shown
            + full_set("2", first="Bo", last="GAP", email="2@x.au", **nmg)
            + [comp("3", "Other", "Does not expire", role="", first="Cy", last="MEEKA", email="3@x.au",
                    employer="Meeka Metals"),
               comp("4", "Other", "Does not expire", role="", first="Di", last="NMGNOROLE", email="4@x.au", **nmg)])
    rows[6] = comp("2", "National Police Clearance", "No document added", first="Bo", last="GAP",
                   email="2@x.au", **nmg)
    flights = [flight("Ann", "SMITH", "2026-10-26", "1@x.au"), flight("Bo", "GAP", "2026-10-26", "2@x.au")]
    r = assess(build_people(rows), flights, [room("3", "2026-10-25"), room("4", "2026-10-25")], TODAY)
    assert [b.person.last for b in r.cleared] == ["SMITH"]
    assert r.not_cleared == []                                          # NMG not-cleared left out
    assert [b.person.last for b in r.no_role] == ["NMGNOROLE"]          # Meeka left out, NMG kept
    assert sorted(b.person.last for b in r.excluded) == ["GAP", "MEEKA"]
    assert r.booked_count == 2
