"""The daily email, from a model.Report. The dashboard page is dashboard.py."""
from datetime import date
from html import escape

import config as C

#: state -> label, shared with the dashboard
LABEL = {
    C.OK: "✓",
    C.MISSING: "Missing",
    C.EXPIRED: "Expired",
    C.NO_DOCUMENT: "No document",
    C.NOT_ON_ROLE: "Not on role",
}

# Inline colours for email clients, which ignore <style>: (text, background) per state,
# NMG style guide, except Missing red / Expired orange / ticks green (Neil, 2026-10-24). The label carries the meaning.
_MAIL_PILL = {
    C.OK: ("#2e7d32", "#E3F1E4"), C.MISSING: ("#a3222f", "#FAE3E5"), C.EXPIRED: ("#9a4f05", "#FBE9D6"),
    C.NO_DOCUMENT: ("#5c4615", "#F8EED5"), C.NOT_ON_ROLE: ("#083045", "#DDE3E7"),
}

_TD = "padding:4px 8px;border-bottom:1px solid #DBDBD3;text-align:left;vertical-align:top"
_TH = _TD + ";border-bottom:2px solid #083045;font-weight:700;white-space:nowrap"


def fmt_day(d: date):
    return f"{d:%a} {d.day} {d:%b}"


def _mail_pill(state):
    fg, bg = _MAIL_PILL[state]
    return (f'<span style="background:{bg};color:{fg};padding:1px 7px;border-radius:9px;font-weight:600;'
            f'white-space:nowrap">{LABEL[state]}</span>')


def email_subject(report, today: date):
    n = len(report.not_cleared)
    return C.SUBJECT.format(count=n, noun="person" if n == 1 else "people", date=f"{today:%d %b %Y}")


def email_html(report):
    window = f"{fmt_day(report.today)} to {fmt_day(report.end)}"
    parts = [
        '<div style="font-family:Aptos,Calibri,Arial,sans-serif;font-size:14px;color:#333334">',
        f"<p>Bookings {window}: <b>{report.booked_count}</b> people booked, "
        f"<b>{len(report.cleared)}</b> cleared, <b style=\"color:#927128\">{len(report.not_cleared)}</b> not cleared, "
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
    parts.append('<p style="color:#6b6b6c;font-size:12px">Medical = Pre Employment Medical, or a Medical Declaration '
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
