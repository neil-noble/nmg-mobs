"""The public dashboard page and the daily email, from a model.Report."""
from datetime import date, datetime
from html import escape

import config as C

CSS = """
:root{--navy:#083045;--river:#55848A;--pale-gold:#B19045;--sand-tint:#F8EED5;--grey-tint:#EDEDE9;
--river-tint:#AAC2C5;--ink:#252423;--muted:#605E5C;--line:#E1DFDD;--canvas:#F3F2F1;
--ok:#1E7B4F;--ok-bg:#E3F1E9;--bad:#B3261E;--bad-bg:#FBE4E2;--warn:#8A5A00;--warn-bg:#FCEFD2;
--na:#5F5E5A;--na-bg:#ECEBE8}
*{box-sizing:border-box}
body{margin:0;background:var(--canvas);color:var(--ink);
font-family:"Proxima Nova",Aptos,"Segoe UI",system-ui,sans-serif;font-size:13px;line-height:1.4}
header{background:var(--navy);color:#fff;border-bottom:3px solid var(--pale-gold)}
header .bar{max-width:1440px;margin:0 auto;padding:10px 16px}
header h1{margin:0;font-size:20px;font-weight:700;line-height:1.15}
header p{margin:2px 0 0;font-size:12px;color:var(--river-tint)}
.canvas{max-width:1440px;margin:0 auto;padding:10px 16px 18px;display:grid;
grid-template-columns:repeat(12,minmax(0,1fr));gap:10px}
.v{grid-column:span var(--span,12);background:#fff;border:1px solid var(--line);border-radius:4px;
padding:10px 12px 12px;box-shadow:0 1px 2px rgba(0,0,0,.05);min-width:0}
.v>h2{margin:0 0 8px;font-size:13px;font-weight:700}
.v>h2 small{font-weight:400;color:var(--muted);font-size:12px}
.note{color:var(--muted);font-size:11.5px;margin:8px 0 0}
.kpis{grid-column:1/-1;display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px}
.v.kpi{grid-column:auto;border-top:3px solid var(--river)}
.kpi.bad{border-top-color:var(--bad)}.kpi.good{border-top-color:var(--ok)}.kpi.warn{border-top-color:var(--pale-gold)}
.kpi b{display:block;font-size:30px;font-weight:700;line-height:1.1;font-variant-numeric:tabular-nums}
.kpi span{font-size:11.5px;color:var(--muted)}
.scroll{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:12.5px}
th,td{padding:5px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
thead th{font-weight:700;border-bottom:2px solid var(--navy);white-space:nowrap}
tbody tr:nth-child(even){background:#FAF9F8}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
td.when{white-space:nowrap;font-variant-numeric:tabular-nums}
td.st{text-align:center;white-space:nowrap}
.pill{display:inline-block;padding:1px 7px;border-radius:9px;font-size:11.5px;font-weight:600}
.pill.ok{background:var(--ok-bg);color:var(--ok)}
.pill.missing{background:var(--bad-bg);color:var(--bad)}
.pill.expired,.pill.nodoc{background:var(--warn-bg);color:var(--warn)}
.pill.norole{background:var(--na-bg);color:var(--na)}
.hbars{display:grid;grid-template-columns:minmax(110px,40%) 1fr;gap:6px 8px;align-items:center}
.brow{display:flex;align-items:center;gap:6px}
.brow i{display:block;height:14px;border-radius:2px;background:var(--bad);min-width:2px}
.brow em{font-style:normal;font-weight:700;font-variant-numeric:tabular-nums}
details summary{cursor:pointer;font-weight:700}
.empty{color:var(--muted);font-style:italic;margin:4px 0}
.canvas>.v{align-self:start}
@media (max-width:900px){.kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.canvas>.v{grid-column:1/-1}}
"""

#: state -> (css class, label)
_PILL = {
    C.OK: ("ok", "✓"),
    C.MISSING: ("missing", "Missing"),
    C.EXPIRED: ("expired", "Expired"),
    C.NO_DOCUMENT: ("nodoc", "No document"),
    C.NOT_ON_ROLE: ("norole", "Not on role"),
}

# Inline colours for email clients, which ignore <style>.
_MAIL_PILL = {
    C.OK: ("#1E7B4F", "#E3F1E9"), C.MISSING: ("#B3261E", "#FBE4E2"), C.EXPIRED: ("#8A5A00", "#FCEFD2"),
    C.NO_DOCUMENT: ("#8A5A00", "#FCEFD2"), C.NOT_ON_ROLE: ("#5F5E5A", "#ECEBE8"),
}


def fmt_day(d: date):
    return f"{d:%a} {d.day} {d:%b}"


def _people(n):
    return f"{n} {'person' if n == 1 else 'people'}"


def _booking_cell(booked):
    first = booked.bookings[0]
    more = len(booked.bookings) - 1
    text = f"{first.kind}: {first.detail}"
    return escape(text) + (f' <span class="note">+{more} more</span>' if more else "")


def _kpis(report):
    checked = len(report.cleared) + len(report.not_cleared)
    ready = f"{round(100 * len(report.cleared) / checked)}%" if checked else "–"
    cards = [
        ("", report.booked_count, "people booked"),
        ("good", len(report.cleared), "cleared to mobilise"),
        ("bad", len(report.not_cleared), "not cleared"),
        ("warn", len(report.no_role), "no work role in PeopleTray"),
        ("", ready, "readiness (of those with a work role)"),
    ]
    return '<div class="kpis">' + "".join(
        f'<div class="v kpi {cls}"><b>{value}</b><span>{escape(label)}</span></div>' for cls, value, label in cards
    ) + "</div>"


def _gap_bars(report):
    counts = report.gap_counts()
    top = max(counts.values()) or 1
    rows = "".join(
        f"<span>{escape(item)}</span><div class=\"brow\"><i style=\"width:{max(1, round(80 * n / top))}%\"></i>"
        f"<em>{n}</em></div>" for item, n in counts.items()
    )
    return (f'<section class="v" style="--span:5"><h2>Missing items <small>people not cleared, by item</small></h2>'
            f'<div class="hbars">{rows}</div>'
            '<p class="note">A person missing several items counts once against each.</p></section>')


def _employer_table(report):
    rows = "".join(
        f'<tr><td>{escape(emp)}</td><td class="num">{booked}</td><td class="num">{bad}</td>'
        f'<td class="num">{round(100 * (booked - bad) / booked)}%</td></tr>'
        for emp, booked, bad in report.by_employer()
    )
    body = (f'<div class="scroll"><table><thead><tr><th>Employer</th><th class="num">Booked</th>'
            f'<th class="num">Not cleared</th><th class="num">Ready</th></tr></thead><tbody>{rows}</tbody></table></div>'
            if rows else '<p class="empty">No bookings in the window.</p>')
    return (f'<section class="v" style="--span:7"><h2>By employer <small>people with a work role</small></h2>'
            f"{body}</section>")


def _not_cleared_table(report):
    if not report.not_cleared:
        return ('<section class="v"><h2>Not cleared to mobilise</h2>'
                '<p class="empty">Everyone booked with a work role has all five items.</p></section>')
    head = "".join(f'<th class="st">{escape(i)}</th>' for i in C.ITEMS)
    rows = []
    for b in report.not_cleared:
        states = b.person.item_states()
        cells = "".join(
            f'<td class="st"><span class="pill {_PILL[states[i]][0]}">{_PILL[states[i]][1]}</span></td>' for i in C.ITEMS
        )
        rows.append(f"<tr><td>{escape(b.person.name)}</td><td>{escape(b.person.employer)}</td>"
                    f'<td class="when">{fmt_day(b.first.day)}</td><td>{_booking_cell(b)}</td>{cells}</tr>')
    return (f'<section class="v"><h2>Not cleared to mobilise <small>{_people(len(report.not_cleared))}, '
            f"earliest booking first</small></h2>"
            f'<div class="scroll"><table><thead><tr><th>Name</th><th>Employer</th><th>First booking</th>'
            f'<th>Booking</th>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
            '<p class="note"><b>Missing</b> = no document added (induction: not yet completed). '
            "<b>Expired</b> = the document or competency has expired. "
            "<b>No document</b> = marked competent but nothing uploaded. "
            "<b>Not on role</b> = the person's work role in PeopleTray does not ask for this item, so it has never "
            "been recorded; fix the work role. Medical = Pre Employment Medical, or a Medical Declaration for "
            "Short Term Workers.</p></section>")


def _simple_table(title, subtitle, items, empty, rows_fn):
    if not items:
        return f'<section class="v"><h2>{escape(title)}</h2><p class="empty">{escape(empty)}</p></section>'
    return (f'<section class="v"><h2>{escape(title)} <small>{escape(subtitle)}</small></h2>'
            f'<div class="scroll"><table><thead><tr><th>Name</th><th>Employer</th><th>First booking</th>'
            f'<th>Booking</th></tr></thead><tbody>{"".join(rows_fn(x) for x in items)}</tbody></table></div></section>')


def _booked_row(b):
    return (f"<tr><td>{escape(b.person.name)}</td><td>{escape(b.person.employer or '(no employer)')}</td>"
            f'<td class="when">{fmt_day(b.first.day)}</td><td>{_booking_cell(b)}</td></tr>')


def _unmatched_row(u):
    first = u.bookings[0]
    return (f"<tr><td>{escape(u.name)}</td><td>{escape(u.employer or '(no employer)')}</td>"
            f'<td class="when">{fmt_day(first.day)}</td><td>{escape(first.kind + ": " + first.detail)}</td></tr>')


def dashboard(report, generated: datetime):
    no_role = _simple_table(
        "No work role in PeopleTray", f"{_people(len(report.no_role))} - cannot be checked until a work role is set",
        report.no_role, "Everyone booked has a work role.", _booked_row)
    unmatched = (_simple_table(
        "Bookings not matched to a PeopleTray profile", "check the name or work email on the booking",
        report.unmatched, "", _unmatched_row) if report.unmatched else "")
    cleared_rows = "".join(_booked_row(b) for b in report.cleared)
    cleared = (f'<section class="v"><details><summary>Cleared to mobilise ({len(report.cleared)})</summary>'
               f'<div class="scroll"><table><thead><tr><th>Name</th><th>Employer</th><th>First booking</th>'
               f"<th>Booking</th></tr></thead><tbody>{cleared_rows}</tbody></table></div></details></section>"
               if report.cleared else "")
    window = f"{fmt_day(report.today)} to {fmt_day(report.end)}"
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="refresh" content="900"><meta name="robots" content="noindex">'
        f"<title>{escape(C.TITLE)}</title><style>{CSS}</style></head><body>"
        f'<header><div class="bar"><h1>{escape(C.TITLE)}</h1>'
        f"<p>Flight and room bookings {window} &middot; checked against Medical, D&amp;A screen, "
        f"police clearance, driver's licence and induction &middot; "
        f"updated {generated:%a %d %b %Y %H:%M} AWST from PeopleTray</p></div></header>"
        f'<main class="canvas">{_kpis(report)}{_gap_bars(report)}{_employer_table(report)}'
        f"{_not_cleared_table(report)}{no_role}{unmatched}{cleared}</main></body></html>"
    )


# ── Email ─────────────────────────────────────────────────────────────────────
_TD = "padding:4px 8px;border-bottom:1px solid #E1DFDD;text-align:left;vertical-align:top"
_TH = _TD + ";border-bottom:2px solid #083045;font-weight:700;white-space:nowrap"


def _mail_pill(state):
    fg, bg = _MAIL_PILL[state]
    return (f'<span style="background:{bg};color:{fg};padding:1px 7px;border-radius:9px;font-weight:600;'
            f'white-space:nowrap">{_PILL[state][1]}</span>')


def email_subject(report, today: date):
    n = len(report.not_cleared)
    return C.SUBJECT.format(count=n, noun="person" if n == 1 else "people", date=f"{today:%d %b %Y}")


def email_html(report):
    window = f"{fmt_day(report.today)} to {fmt_day(report.end)}"
    parts = [
        '<div style="font-family:Calibri,Arial,sans-serif;font-size:14px;color:#252423">',
        f"<p>Bookings {window}: <b>{report.booked_count}</b> people booked, "
        f"<b>{len(report.cleared)}</b> cleared, <b style=\"color:#B3261E\">{len(report.not_cleared)}</b> not cleared, "
        f"<b>{len(report.no_role)}</b> with no work role in PeopleTray.</p>",
        f'<p>Live dashboard: <a href="{C.DASHBOARD_URL}">{C.DASHBOARD_URL}</a></p>',
    ]
    if report.not_cleared:
        head = "".join(f'<th style="{_TH};text-align:center">{escape(i)}</th>' for i in C.ITEMS)
        rows = []
        for b in report.not_cleared:
            states = b.person.item_states()
            cells = "".join(f'<td style="{_TD};text-align:center">{_mail_pill(states[i])}</td>' for i in C.ITEMS)
            rows.append(f'<tr><td style="{_TD}">{escape(b.person.name)}</td><td style="{_TD}">'
                        f'{escape(b.person.employer)}</td><td style="{_TD};white-space:nowrap">{fmt_day(b.first.day)}'
                        f'</td><td style="{_TD}">{escape(b.first.kind + ": " + b.first.detail)}</td>{cells}</tr>')
        parts.append(f"<h3 style=\"margin:16px 0 6px\">Not cleared to mobilise ({len(report.not_cleared)})</h3>"
                     f'<table style="border-collapse:collapse;font-size:13px"><tr><th style="{_TH}">Name</th>'
                     f'<th style="{_TH}">Employer</th><th style="{_TH}">First booking</th><th style="{_TH}">Booking'
                     f'</th>{head}</tr>{"".join(rows)}</table>')
    if report.no_role:
        items = "".join(f"<li>{escape(b.person.name)} ({escape(b.person.employer or 'no employer')}) - "
                        f"{fmt_day(b.first.day)}</li>" for b in report.no_role)
        parts.append(f"<h3 style=\"margin:16px 0 6px\">No work role in PeopleTray ({len(report.no_role)})</h3>"
                     f"<p>These people cannot be checked until a work role is set.</p><ul>{items}</ul>")
    if report.unmatched:
        items = "".join(f"<li>{escape(u.name)} ({escape(u.employer or 'no employer')}) - "
                        f"{fmt_day(u.bookings[0].day)}</li>" for u in report.unmatched)
        parts.append(f"<h3 style=\"margin:16px 0 6px\">Bookings not matched to a PeopleTray profile "
                     f"({len(report.unmatched)})</h3><ul>{items}</ul>")
    parts.append('<p style="color:#605E5C;font-size:12px">Medical = Pre Employment Medical, or a Medical Declaration '
                 "for Short Term Workers. \"Not on role\" means the person's PeopleTray work role does not ask for "
                 "the item. This check reports bookings; it cannot stop them.</p></div>")
    return "".join(parts)


def email_text(report):
    lines = [f"Bookings {fmt_day(report.today)} to {fmt_day(report.end)}: {report.booked_count} booked, "
             f"{len(report.cleared)} cleared, {len(report.not_cleared)} not cleared, "
             f"{len(report.no_role)} with no work role.", f"Dashboard: {C.DASHBOARD_URL}", ""]
    for b in report.not_cleared:
        gaps = ", ".join(f"{i} ({s})" for i, s in b.person.gaps().items())
        lines.append(f"{b.person.name} | {b.person.employer} | {fmt_day(b.first.day)} | {gaps}")
    return "\n".join(lines) + "\n"
