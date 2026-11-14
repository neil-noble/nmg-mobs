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
    excluded: list = field(default_factory=list)   # left out by employer; never shown or counted

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


def _match(people, flights, rooms, start: date, end: date, split_stays=False):
    """Bookings from start..end per employeeId, plus bookings matched to no profile.

    Rooms: one booking per person (first night + night count), or with split_stays one per run of
    consecutive nights, so a later return trip reads as its own booking."""
    by_email = {p.email: eid for eid, p in people.items() if p.email}
    by_name = defaultdict(list)
    for eid, p in people.items():
        by_name[(p.first.lower(), p.last.lower())].append(eid)

    bookings = defaultdict(set)        # employeeId -> {Booking}
    unmatched = {}                     # name -> Unmatched
    for row in flights:
        day = _day(row["flightDate"])
        if not (start <= day <= end and _live_flight(row)):
            continue
        booking = Booking(day, "Flight", _flight_detail(row))
        eid = by_email.get((row.get("workEmail") or "").strip().lower())
        if eid is None:
            key = ((row.get("firstName") or "").strip().lower(), (row.get("lastName") or "").strip().lower())
            candidates = by_name.get(key, [])
            eid = candidates[0] if len(candidates) == 1 else None
        if eid is None:
            name = f"{(row.get('lastName') or '').strip().upper()}, {(row.get('firstName') or '').strip()}"
            u = unmatched.setdefault(name, Unmatched(name, (row.get("employer") or "").strip(), []))
            u.bookings.append(booking)
            continue
        bookings[eid].add(booking)

    rooms_by_person = defaultdict(list)
    for row in rooms:
        day = _day(row["dateOfBooking"])
        if start <= day <= end:
            rooms_by_person[str(row.get("employeeId") or "").strip()].append((day, row))
    for eid, nights in rooms_by_person.items():
        if eid not in people:
            row = nights[0][1]
            name = f"{(row.get('personLastName') or '').strip().upper()}, {(row.get('personFirstName') or '').strip()}"
            u = unmatched.setdefault(name, Unmatched(name, (row.get("employer") or "").strip(), []))
            u.bookings.extend(Booking(d, "Room", (r.get("roomCamp") or "").strip()) for d, r in nights)
            continue
        nights.sort(key=lambda n: n[0])
        stays = [[nights[0]]]
        for night in nights[1:]:
            if split_stays and (night[0] - stays[-1][-1][0]).days > 1:
                stays.append([night])
            else:
                stays[-1].append(night)
        # A run of room nights reads as one booking: show the first night of the stay.
        for stay in stays:
            first_day, first_row = stay[0]
            bookings[eid].add(Booking(first_day, "Room", f"{(first_row.get('roomCamp') or '').strip()}, "
                                                        f"{len({d for d, _ in stay})} night(s)"))
    for u in unmatched.values():
        u.bookings.sort(key=lambda b: (b.day, b.kind))
    return bookings, unmatched


def _status(person):
    """'r' no work role, 'n' not cleared, 'c' cleared."""
    if not person.roles:
        return "r"
    return "n" if person.gaps() else "c"


def _excluded(person, status):
    employer = person.employer.strip().casefold()
    if status == "r":
        return employer in {e.casefold() for e in C.NO_ROLE_EXCLUDED_EMPLOYERS}
    if status == "n":
        return employer in {e.casefold() for e in C.NOT_CLEARED_EXCLUDED_EMPLOYERS}
    return False


def assess(people, flights, rooms, today: date, days=C.LOOKAHEAD_DAYS) -> Report:
    """Everyone booked in the window (the daily email)."""
    end = today + timedelta(days=days - 1)
    bookings, unmatched = _match(people, flights, rooms, today, end)
    cleared, not_cleared, no_role, excluded = [], [], [], []
    for eid, items in bookings.items():
        booked = Booked(people[eid], sorted(items, key=lambda b: (b.day, b.kind)))
        status = _status(booked.person)
        if _excluded(booked.person, status):
            excluded.append(booked)
        else:
            {"r": no_role, "n": not_cleared, "c": cleared}[status].append(booked)
    order = lambda b: (b.first.day, b.person.last.lower(), b.person.first.lower())
    return Report(today, end, sorted(cleared, key=order), sorted(not_cleared, key=order),
                  sorted(no_role, key=order),
                  sorted(unmatched.values(), key=lambda u: (u.bookings[0].day, u.name)), excluded)


@dataclass
class Worker:
    person: Person
    status: str        # "c" cleared, "n" not cleared, "r" no work role
    bookings: list     # upcoming bookings, earliest first; empty = no booking

    @property
    def next(self):
        return self.bookings[0] if self.bookings else None


@dataclass
class Workforce:
    """Every worker in PeopleTray, booked or not (the dashboard; Neil, 2026-11-15)."""
    today: date
    end: date          # end of the booking window (the email's 14 days)
    horizon: date      # bookings are looked for up to this day
    workers: list
    unmatched: list
    excluded: int = 0

    def in_window(self, worker):
        return worker.next is not None and worker.next.day <= self.end


def assess_all(people, flights, rooms, today: date, horizon_days=C.HORIZON_DAYS,
               days=C.LOOKAHEAD_DAYS) -> Workforce:
    end = today + timedelta(days=days - 1)
    horizon = today + timedelta(days=horizon_days - 1)
    bookings, unmatched = _match(people, flights, rooms, today, horizon, split_stays=True)
    workers, excluded = [], 0
    for eid, person in people.items():
        status = _status(person)
        if _excluded(person, status):
            excluded += 1
            continue
        workers.append(Worker(person, status, sorted(bookings.get(eid, ()), key=lambda b: (b.day, b.kind))))
    workers.sort(key=lambda w: (w.next is None, w.next.day if w.next else today,
                                w.person.last.lower(), w.person.first.lower()))
    return Workforce(today, end, horizon, workers,
                     sorted(unmatched.values(), key=lambda u: (u.bookings[0].day, u.name)), excluded)
