"""Every tunable for the NMG mobilisation compliance check lives here."""
from zoneinfo import ZoneInfo

AWST = ZoneInfo("Australia/Perth")

# ── PeopleTray ────────────────────────────────────────────────────────────────
PT_BASE_URL = "https://api-peopletray.azurewebsites.net"
COMPLIANCE_PATH = "/api/v2/powerbi/personworkrolecompetencycompliance"
FLIGHTS_PATH = "/api/v2/powerbi/flightbookings"
ROOMS_PATH = "/api/v2/powerbi/roombookings"

#: Bookings from today up to this many days ahead are checked (Neil, 2026-10-24).
LOOKAHEAD_DAYS = 14

# ── The five mobilisation items (Neil, 2026-10-24) ────────────────────────────
MEDICAL = "Medical"
DRUG_ALCOHOL = "D&A Screen"
POLICE = "Police Clearance"
LICENCE = "Driver's Licence"
INDUCTION = "Induction"
ITEMS = (MEDICAL, DRUG_ALCOHOL, POLICE, LICENCE, INDUCTION)

#: PeopleTray compliance / competency name -> item. Medical is special-cased in model.py.
SOURCE_NAMES = {
    "Pre Employment Medical": MEDICAL,
    "Medical Declaration": MEDICAL,
    "Drug and Alcohol Screen": DRUG_ALCOHOL,
    "National Police Clearance": POLICE,
    "Drivers License - C (Car)": LICENCE,
    "Crown Prince Project Site Induction": INDUCTION,
}
PRE_EMPLOYMENT_MEDICAL = "Pre Employment Medical"
MEDICAL_DECLARATION = "Medical Declaration"
#: Short Term Workers need a Medical Declaration instead of a Pre Employment Medical (Neil, 2026-10-24).
STW_ROLE_PREFIX = "*Short Term Worker"

# ── Employers left out of a section (Neil, 2026-10-24) ────────────────────────
# Matched case-insensitively against the PeopleTray employer. People left out appear nowhere on
# the dashboard or in the email, and are not counted.
NOT_CLEARED_EXCLUDED_EMPLOYERS = ("New Murchison Gold Ltd",)
NO_ROLE_EXCLUDED_EMPLOYERS = ("Meeka Metals", "WestGold")

# ── Item states ───────────────────────────────────────────────────────────────
OK = "ok"
MISSING = "missing"              # "No document added" / competency "WR Requirement"
EXPIRED = "expired"
NO_DOCUMENT = "no document"      # competency marked Competent, but nothing uploaded
NOT_ON_ROLE = "not on work role" # the person's work role does not ask for it at all

# ── Email ─────────────────────────────────────────────────────────────────────
SMTP_HOST = "smtp-relay.brevo.com"
SMTP_PORT = 587
FROM_ADDRESS = "neil.noble@emergencyservicesaustralia.com.au"
FROM_NAME = "NMG Mobilisation Compliance"
SUBJECT = "Mobilisation compliance - {count} booked {noun} not cleared - {date}"
#: Daily report time; the first hourly build at or after it sends the email.
SEND_AT_HOUR = 5   # Neil, 2026-10-25 (was 6)
SENT_MARKER = "mobs-sent-{date}"
ALERT_MARKER = "mobs-alerted-{date}"

# ── Dashboard ─────────────────────────────────────────────────────────────────
TITLE = "NMG Mobilisation Compliance"
DASHBOARD_URL = "https://www.emergencyservicesaustralia.com.au/nmgmobs"
