"""Command line for the workflow.

  build   fetch from PeopleTray, write out/index.html (dashboard) and the email parts
  due     is today's email still owed? (writes due=yes|no to $GITHUB_OUTPUT)
  send    email the report built by `build`
  alert   email a failure notice

The repo is public: nothing here prints a name. Logs carry counts only.
"""
import argparse
import json
import os
import smtplib
import sys
import urllib.request
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

import config as C
import dashboard
import peopletray
import render
from model import assess, build_people


def now_awst():
    return datetime.now(C.AWST)


def cmd_build(args):
    now = now_awst()
    today = now.date()
    end = today + timedelta(days=C.LOOKAHEAD_DAYS - 1)
    people = build_people(peopletray.fetch_compliance())
    report = assess(people, peopletray.fetch_flight_bookings(today, end),
                    peopletray.fetch_room_bookings(today, end), today)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(dashboard.page(report, now), encoding="utf-8")
    (out / "email.html").write_text(render.email_html(report), encoding="utf-8")
    (out / "email.txt").write_text(render.email_text(report), encoding="utf-8")
    (out / "subject.txt").write_text(render.email_subject(report, today), encoding="utf-8")
    print(f"{len(people)} profiles; window {today} to {end}; booked {report.booked_count}: "
          f"cleared {len(report.cleared)}, not cleared {len(report.not_cleared)}, "
          f"no work role {len(report.no_role)}, unmatched {len(report.unmatched)}, "
          f"excluded by employer {len(report.excluded)}")
    print("missing by item: " + ", ".join(f"{k} {v}" for k, v in report.gap_counts().items()))


def _output(**values):
    """Step outputs for the workflow (a no-op when run by hand)."""
    with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a", encoding="utf-8") as fh:
        fh.writelines(f"{k}={v}\n" for k, v in values.items())


def _marker_exists(name, repo, token):
    url = f"https://api.github.com/repos/{repo}/actions/artifacts?name={name}&per_page=1"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}",
                                               "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())["total_count"] > 0


def cmd_due(args):
    now = now_awst()
    marker = C.SENT_MARKER.format(date=now.date().isoformat())
    if args.force:
        due, why = True, "forced"
    elif now.hour < C.SEND_AT_HOUR:
        due, why = False, f"before {C.SEND_AT_HOUR:02d}:00 AWST"
    elif _marker_exists(marker, os.environ["GITHUB_REPOSITORY"], os.environ["GH_TOKEN"]):
        due, why = False, "already sent today"
    else:
        due, why = True, "not yet sent today"
    print(f"email due: {'yes' if due else 'no'} ({why})")
    _output(due="yes" if due else "no", marker=marker)


def _recipients():
    to = [a.strip() for a in os.environ.get("MOBS_REPORT_TO", "").split(",") if a.strip()]
    if not to:
        sys.exit("MOBS_REPORT_TO is not set")
    return to


def _send(subject, text, html, to):
    user, password = os.environ.get("BREVO_USERNAME", ""), os.environ.get("BREVO_PASSWORD", "")
    if not user or not password:
        sys.exit("BREVO_USERNAME / BREVO_PASSWORD are not set")
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((C.FROM_NAME, C.FROM_ADDRESS))
    msg["To"] = ", ".join(to)
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")
    with smtplib.SMTP(C.SMTP_HOST, C.SMTP_PORT, timeout=60) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg, from_addr=C.FROM_ADDRESS, to_addrs=to)


def cmd_send(args):
    out = Path(args.out)
    to = _recipients()
    _send((out / "subject.txt").read_text(encoding="utf-8"), (out / "email.txt").read_text(encoding="utf-8"),
          (out / "email.html").read_text(encoding="utf-8"), to)
    print(f"report emailed to {len(to)} recipient(s)")


def cmd_alert(args):
    """At most one failure alert a day: a PeopleTray outage would otherwise alert every hour."""
    marker = C.ALERT_MARKER.format(date=now_awst().date().isoformat())
    if _marker_exists(marker, os.environ["GITHUB_REPOSITORY"], os.environ["GH_TOKEN"]):
        print("failure alert already sent today")
        _output(alerted="no", marker=marker)
        return
    run_url = os.environ.get("RUN_URL", "")
    _send("Mobilisation compliance check FAILED",
          f"The mobilisation compliance build failed, so the dashboard and/or today's email may be stale.\n\n"
          f"Run log: {run_url}\n", None, _recipients())
    print("failure alert sent")
    _output(alerted="yes", marker=marker)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("build")
    p.add_argument("--out", default="out")
    p.set_defaults(fn=cmd_build)
    p = sub.add_parser("due")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_due)
    p = sub.add_parser("send")
    p.add_argument("--out", default="out")
    p.set_defaults(fn=cmd_send)
    sub.add_parser("alert").set_defaults(fn=cmd_alert)
    args = parser.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
