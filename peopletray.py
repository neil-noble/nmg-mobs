"""Authenticated GET against the PeopleTray API, with retries and paging."""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

from config import COMPLIANCE_PATH, FLIGHTS_PATH, PT_BASE_URL, ROOMS_PATH

# Shared with the other NMG projects; the key is on line 2, under a label line.
KEY_FILE = Path(r"C:\claude\PeopleTray DAS\reference\PT API Key for NMG.txt")
ATTEMPTS = 4


class PeopleTrayError(RuntimeError):
    """PeopleTray could not be reached, or answered badly, after every retry."""


def load_key(env=os.environ, key_file=KEY_FILE):
    key = (env.get("PT_API_KEY") or "").strip()
    if key:
        return key
    try:
        return Path(key_file).read_text(encoding="utf-8-sig").splitlines()[1].strip()
    except (OSError, IndexError):
        raise PeopleTrayError(f"No PeopleTray key: set PT_API_KEY or provide {key_file}") from None


def get(path, params=None, opener=urllib.request.urlopen, sleep=time.sleep):
    url = PT_BASE_URL + path + ("?" + urllib.parse.urlencode(params) if params else "")
    request = urllib.request.Request(url, headers={"X-API-Key": load_key()})
    last_error = None
    for attempt in range(ATTEMPTS):
        if attempt:
            sleep(5 * 2 ** (attempt - 1))
        try:
            with opener(request, timeout=120) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            # A bad key or query will not fix itself. PeopleTray answers a bad key with 400.
            if 400 <= error.code < 500 and error.code != 429:
                raise PeopleTrayError(f"PeopleTray {path} refused with HTTP {error.code}") from error
            last_error = error
        except (OSError, ValueError) as error:
            last_error = error
    raise PeopleTrayError(f"PeopleTray {path} failed after {ATTEMPTS} attempts: {last_error}")


def dedupe(rows):
    """Drop rows identical in every field - PeopleTray returns exact duplicates. Keeps order."""
    seen, unique = set(), []
    for row in rows:
        key = json.dumps(row, sort_keys=True)
        if key not in seen:
            seen.add(key)
            unique.append(row)
    return unique


def _as_list(payload, what):
    if not isinstance(payload, list):
        raise PeopleTrayError(f"{what}: expected a list from PeopleTray, got {type(payload).__name__}")
    return payload


def fetch_compliance(**kw):
    """Every person's work-role compliance and competency rows (paged, ~17 pages)."""
    rows, page = [], get(COMPLIANCE_PATH, **kw)
    while True:
        if not isinstance(page, dict) or "data" not in page:
            raise PeopleTrayError("compliance: expected a paged response from PeopleTray")
        rows.extend(page["data"])
        nxt = page.get("nextPageLink")
        if not nxt:
            return rows
        page = get(nxt.replace(PT_BASE_URL, ""), **kw)


def fetch_flight_bookings(start: date, end: date, **kw):
    params = {"fromDate": start.isoformat(), "toDate": end.isoformat()}
    return dedupe(_as_list(get(FLIGHTS_PATH, params, **kw), "flightbookings"))


def fetch_room_bookings(start: date, end: date, **kw):
    params = {"fromDate": start.isoformat(), "toDate": end.isoformat()}
    return dedupe(_as_list(get(ROOMS_PATH, params, **kw), "roombookings"))
