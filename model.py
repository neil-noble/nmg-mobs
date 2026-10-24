"""Who is booked to travel or stay, and which of the five mobilisation items they lack.

Pure functions over PeopleTray rows - no network, no clock.
"""
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import config as C

#: When a person has several rows for one item (one per work role), the best state wins.
_RANK = {C.OK: 0, C.NO_DOCUMENT: 1, C.EXPIRED: 2, C.MISSING: 3, C.NOT_ON_ROLE: 4}
_OK_PREFIXES = ("Does not expire", "Expiry on", "Expiring on")


@dataclass
class Person:
    employee_id: str
    first: str
    last: str
    employer: str
    workgroup: str
    email: str
    roles: set = field(default_factory=set)
    #: source compliance/competency name -> best state seen
    sources: dict = field(default_factory=dict)

    @property
    def name(self):
        return f"{self.last.upper()}, {self.first}".strip(", ")

    @property
    def is_stw(self):
        return any(r.startswith(C.STW_ROLE_PREFIX) for r in self.roles)

    def item_states(self):
        """item -> state, for the five items."""
        states = {}
        for item in C.ITEMS:
            if item == C.MEDICAL:
                names = [C.PRE_EMPLOYMENT_MEDICAL]
                if self.is_stw:
                    names.append(C.MEDICAL_DECLARATION)
            else:
                names = [n for n, i in C.SOURCE_NAMES.items() if i == item]
            found = [self.sources[n] for n in names if n in self.sources]
            states[item] = min(found, key=_RANK.get) if found else C.NOT_ON_ROLE
        return states

    def gaps(self):
        return {item: s for item, s in self.item_states().items() if s != C.OK}


def row_state(row):
    """State of one compliance or competency row."""
    if row.get("complianceName"):
        status = row.get("complianceStatus") or ""
        if status.startswith("Expired"):
            return C.EXPIRED
        return C.OK if status.startswith(_OK_PREFIXES) else C.MISSING
    status = row.get("competencyStatus") or ""
    if status == "Competent":
        return C.OK if row.get("competencyDocumentUploaded") else C.NO_DOCUMENT
    return C.EXPIRED if status == "Expired" else C.MISSING


def build_people(rows):
    """employeeId -> Person, from the work-role compliance feed."""
    people = {}
    for row in rows:
        eid = str(row.get("employeeId") or "").strip()
        if not eid:
            continue
        p = people.get(eid)
        if p is None:
            p = people[eid] = Person(
                employee_id=eid,
                first=(row.get("firstName") or "").strip(),
                last=(row.get("lastName") or "").strip(),
                employer=(row.get("employer") or "").strip(),
                workgroup=(row.get("workgroup") or "").strip(),
                email=(row.get("workEmail") or "").strip().lower(),
            )
        role = (row.get("workRole") or "").strip()
        if role:
            p.roles.add(role)
        source = row.get("complianceName") or row.get("competencyName")
        if source in C.SOURCE_NAMES:
            state = row_state(row)
            old = p.sources.get(source)
            if old is None or _RANK[state] < _RANK[old]:
                p.sources[source] = state
    return people


@dataclass(frozen=True)
class Booking:
    day: date
    kind: str      # "Flight" or "Room"
    detail: str


@dataclass
class Booked:
    person: Person
    bookings: list

    @property
    def first(self):
        return self.bookings[0]


@dataclass
class Unmatched:
    name: str
    employer: str
    bookings: list


@dataclass
class Report:
    today: date
    end: date
    cleared: list
    not_cleared: list
    no_role: list
    unmatched: list

    @property
    def booked_count(self):
        return len(self.cleared) + len(self.not_cleared) + len(self.no_role) + len(self.unmatched)

    def gap_counts(self):
        """item -> number of not-cleared people lacking it."""
        counts = {item: 0 for item in C.ITEMS}
        for b in self.not_cleared:
            for item in b.person.gaps():
                counts[item] += 1
        return counts

    def by_employer(self):
        """employer -> (booked people with a work role, not cleared), most not-cleared first."""
        table = defaultdict(lambda: [0, 0])
        for b in self.cleared:
            table[b.person.employer or "(no employer)"][0] += 1
        for b in self.not_cleared:
            row = table[b.person.employer or "(no employer)"]
            row[0] += 1
            row[1] += 1
        return sorted(((k, v[0], v[1]) for k, v in table.items()), key=lambda r: (-r[2], -r[1], r[0]))


def _day(value):
    return datetime.fromisoformat(value).date()


def _flight_detail(row):
    route = f"{(row.get('departurePort') or '?').strip()} to {(row.get('arrivalPort') or '?').strip()}"
    status = row.get("bookingStatus") or ""
    return route + (f" ({status.lower()})" if status and status != "Booked" else "")


def _live_flight(row):
    return not row.get("cancel") and (row.get("bookingStatus") or "") != "Cancelled"


def assess(people, flights, rooms, today: date, days=C.LOOKAHEAD_DAYS) -> Report:
    end = today + timedelta(days=days - 1)
    by_email = {p.email: eid for eid, p in people.items() if p.email}
    by_name = defaultdict(list)
    for eid, p in people.items():
        by_name[(p.first.lower(), p.last.lower())].append(eid)

    bookings = defaultdict(set)        # employeeId -> {Booking}
    unmatched = {}                     # (first, last) -> Unmatched
    for row in flights:
        day = _day(row["flightDate"])
        if not (today <= day <= end and _live_flight(row)):
            continue
        booking = Booking(day, "Flight", _flight_detail(row))
        eid = by_email.get((row.get("workEmail") or "").strip().lower())
        if eid is None:
            key = ((row.get("firstName") or "").strip().lower(), (row.get("lastName") or "").strip().lower())
            candidates = by_name.get(key, [])
            eid = candidates[0] if len(candidates) == 1 else None
        if eid is None:
            name = f"{(row.get('lastName') or '').upper()}, {row.get('firstName') or ''}"
            u = unmatched.setdefault(name, Unmatched(name, (row.get("employer") or "").strip(), []))
            u.bookings.append(booking)
            continue
        bookings[eid].add(booking)

    rooms_by_person = defaultdict(list)
    for row in rooms:
        day = _day(row["dateOfBooking"])
        if today <= day <= end:
            rooms_by_person[str(row.get("employeeId") or "").strip()].append((day, row))
    for eid, nights in rooms_by_person.items():
        if eid not in people:
            row = nights[0][1]
            name = f"{(row.get('personLastName') or '').upper()}, {row.get('personFirstName') or ''}"
            u = unmatched.setdefault(name, Unmatched(name, (row.get("employer") or "").strip(), []))
            u.bookings.extend(Booking(d, "Room", (r.get("roomCamp") or "").strip()) for d, r in nights)
            continue
        # A run of room nights reads as one booking: show the first night of the stay.
        nights.sort(key=lambda n: n[0])
        first_day, first_row = nights[0]
        bookings[eid].add(Booking(first_day, "Room", f"{(first_row.get('roomCamp') or '').strip()}, "
                                                    f"{len({d for d, _ in nights})} night(s)"))

    cleared, not_cleared, no_role = [], [], []
    for eid, items in bookings.items():
        booked = Booked(people[eid], sorted(items, key=lambda b: (b.day, b.kind)))
        if not booked.person.roles:
            no_role.append(booked)
        elif booked.person.gaps():
            not_cleared.append(booked)
        else:
            cleared.append(booked)
    for u in unmatched.values():
        u.bookings.sort(key=lambda b: (b.day, b.kind))
    order = lambda b: (b.first.day, b.person.last.lower(), b.person.first.lower())
    return Report(today, end, sorted(cleared, key=order), sorted(not_cleared, key=order),
                  sorted(no_role, key=order),
                  sorted(unmatched.values(), key=lambda u: (u.bookings[0].day, u.name)))
