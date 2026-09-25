"""Build a sample-data file for the quarantine tracker.

Writes outputs/sample-data.json in the app's own backup format (version 3), so it
loads through the Restore button in the header. Nothing here touches Firebase.

Dates are computed relative to the moment the script runs, so the sample set always
contains parts that are OK (<7 days), Warning (7-13) and Critical (14+).

Usage:  python scripts/make_sample_data.py
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "outputs" / "sample-data.json"
NOW = datetime.now(timezone.utc)


def iso(days_ago, hour=13, minute=0):
    """An ISO timestamp days_ago days back, at a plausible shift hour."""
    d = (NOW - timedelta(days=days_ago)).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )
    return d.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def epoch_ms(iso_str):
    return int(
        datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%S.000Z")
        .replace(tzinfo=timezone.utc)
        .timestamp()
        * 1000
    )


def simple_hash(s):
    """Port of simpleHash() in index.html: 32-bit signed, base 36."""
    h = 0
    for ch in s:
        h = ((h << 5) - h) + ord(ch)
        h &= 0xFFFFFFFF
    if h >= 0x80000000:
        h -= 0x100000000
    if h == 0:
        return "0"
    neg, h = h < 0, abs(h)
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    while h:
        h, r = divmod(h, 36)
        out = digits[r] + out
    return ("-" + out) if neg else out


def stringify(obj):
    """Match JavaScript's JSON.stringify output for these records."""
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)


# Part numbers stay on the default CSP- prefix. Which prefix the pilot should really
# use is still an open question in memory/decisions.md, so sample data must not
# quietly answer it by seeding customer-coded numbers.

# Parts that came and went. These sit in the log only, and their numbers are lower
# than every active part so auto-numbering still lands on the next free CSP number.
COMPLETED = [
    # part#, description, sent from, by, zone, SO, days-ago in, days-ago out
    ("CSP-001", "Ryder Cab Door Decal Set", "Ryder", "Sarah L", "1", "SO-10344", 40, 33),
    ("CSP-002", "Enterprise Fleet Logo Panel Wrap", "Enterprise", "Grant Motley", "3", "SO-10351", 35, 28),
    ("CSP-003", "Hertz Rear Roll-Up Door Graphic", "Hertz", "Dave R", "4", "SO-10358", 30, 12),
    ("CSP-004", "U-Haul Box Side Mural Panel", "U-Haul", "Mike T", "2", "SO-10362", 26, 20),
]

# Parts still in quarantine. Days-ago values are chosen to spread across the three
# status bands and to exercise every stage and condition badge.
ACTIVE = [
    dict(num="CSP-005", desc="Ryder Reflective Tape Kit", frm="Ryder", by="Sarah L",
         zone="1", so="SO-10377", days=21, stage="Escalated",
         condition="Significant damage",
         damage="Two rolls arrived with the adhesive backing torn",
         notes="Replacement requested from Ryder",
         escalated_to="Lori (purchasing)",
         thread=[("Sarah L", 19, "Adhesive backing torn on two rolls. Cannot install."),
                 ("Lori", 16, "Opened a claim with Ryder. Replacement ships this week.")]),
    dict(num="CSP-006", desc="Ryder DOT Number Decal", frm="Ryder", by="Sarah L",
         zone="1", so="SO-10377", days=19, stage="Checked In",
         condition="No damage", damage="", notes="", thread=[]),
    dict(num="CSP-007", desc="Penske Rear Chevron Reflective Strip", frm="Penske", by="Mike T",
         zone="2", so="SO-10381", days=16, stage="Missing",
         condition="No damage", damage="",
         notes="Not on the zone shelf at the Monday count",
         thread=[("Mike T", 3, "Walked zones 1 through 4, no sign of it. Flagged as missing.")]),
    dict(num="CSP-008", desc="Penske Fleet Number Decal", frm="Penske", by="Mike T",
         zone="2", so="SO-10381", days=12, stage="Checked In",
         condition="No damage", damage="", notes="", thread=[]),
    dict(num="CSP-009", desc="Enterprise Fleet Logo Panel Wrap", frm="Enterprise", by="Grant Motley",
         zone="3", so="SO-10391", days=10, stage="Checked In",
         condition="Minor damage", damage="Corner of the wrap creased in shipping",
         notes="", thread=[]),
    dict(num="CSP-010", desc="Enterprise DOT Number Decal", frm="Enterprise", by="Grant Motley",
         zone="3", so="SO-10391", days=9, stage="Checked In",
         condition="No damage", damage="", notes="", thread=[]),
    dict(num="CSP-011", desc="U-Haul Box Side Mural Panel", frm="U-Haul", by="Dave R",
         zone="4", so="SO-10398", days=8, stage="Checked In",
         condition="Minor damage", damage="Small scuff along the bottom edge",
         notes="Scuff is below the body line, Dawn okayed installing it",
         thread=[("Dave R", 8, "Scuffed on arrival. Photographed before it went on the shelf.")]),
    dict(num="CSP-012", desc="Hertz Gold Stripe Accent Kit", frm="Hertz", by="Dave R",
         zone="1", so="SO-10402", days=5, stage="Checked In",
         condition="No damage", damage="", notes="", thread=[]),
    dict(num="CSP-013", desc="Hertz Rear Roll-Up Door Graphic", frm="Hertz", by="Dave R",
         zone="4", so="SO-10402", days=4, stage="Checked In",
         condition="No damage", damage="", notes="", thread=[]),
    dict(num="CSP-014", desc="Budget Cab Door Number Decal", frm="Budget", by="Sarah L",
         zone="2", so="SO-10406", days=3, stage="Checked In",
         condition="No damage", damage="", notes="", thread=[]),
    # The whole point of Rev P: a part logged with nothing but a zone is still a win.
    dict(num="CSP-015", desc="", frm="", by="", zone="3", so="", days=1,
         stage="Checked In", condition="No damage", damage="", notes="", thread=[]),
    dict(num="CSP-016", desc="Penske Mudflap Logo Pair", frm="Penske", by="Mike T",
         zone="4", so="SO-10411", days=0, stage="Checked In",
         condition="No damage", damage="", notes="", thread=[]),
]


def main():
    events = []  # (date, entry without the chain fields)

    for num, desc, frm, by, zone, so, d_in, d_out in COMPLETED:
        in_date = iso(d_in, hour=9, minute=15)
        out_date = iso(d_out, hour=14, minute=30)
        events.append((in_date, {
            "partNumber": num, "description": desc, "action": "CHECK IN",
            "date": in_date, "user": by, "sentFrom": frm, "shelf": zone,
            "salesOrder": so, "duration": None, "notes": "",
        }))
        events.append((out_date, {
            "partNumber": num, "unitNumber": "", "description": desc,
            "action": "CHECK OUT", "date": out_date, "user": by, "sentFrom": frm,
            "shelf": zone, "salesOrder": so, "duration": d_in - d_out, "notes": "",
        }))

    parts = []
    for i, p in enumerate(ACTIVE):
        in_date = iso(p["days"], hour=8 + (i % 8), minute=(i * 7) % 60)
        part = {
            "id": "sample" + p["num"].lower().replace("-", ""),
            "partNumber": p["num"],
            "description": p["desc"],
            "checkinDate": in_date,
            "sentFrom": p["frm"],
            "checkedInBy": p["by"],
            "shelf": p["zone"],
            "notes": p["notes"],
            "notesThread": [
                {"author": a, "text": t, "date": iso(days, hour=10, minute=45)}
                for a, days, t in p["thread"]
            ],
            "salesOrder": p["so"],
            "stage": p["stage"],
            "condition": p["condition"],
            "damageNotes": p["damage"],
        }
        if p.get("escalated_to"):
            part["escalatedTo"] = p["escalated_to"]
        parts.append(part)
        events.append((in_date, {
            "partNumber": p["num"], "description": p["desc"], "action": "CHECK IN",
            "date": in_date, "user": p["by"], "sentFrom": p["frm"], "shelf": p["zone"],
            "salesOrder": p["so"], "duration": None, "notes": p["notes"],
        }))

    # The audit log is append-only and hash chained, so it has to be built in the
    # order the events actually happened.
    events.sort(key=lambda e: e[0])
    log, prev_hash = [], ""
    for i, (date, entry) in enumerate(events, start=1):
        entry["logId"] = i
        entry["timestamp"] = epoch_ms(date)
        entry["hash"] = simple_hash(stringify(entry) + prev_hash)
        prev_hash = entry["hash"]
        log.append(entry)

    payload = {
        "version": 3,
        "exportedAt": NOW.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "parts": parts,
        "log": log,
        "logId": len(log),
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("Wrote " + str(OUT) + " - " + str(len(parts)) + " active part(s), "
          + str(len(log)) + " log record(s)")


if __name__ == "__main__":
    main()
