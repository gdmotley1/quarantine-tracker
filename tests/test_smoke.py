'''Smoke tests. The gate for this project.

The whole app is one HTML file with an inline script, so the gate parses that file
and asserts the invariants that have actually bitten us. Add a test alongside every
behaviour worth keeping. If a test is in the way, fix the code or change the test
deliberately. Never delete one to make the suite green.

Run: python -m pytest tests/ -q
'''

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
PROCESS_FLOW = ROOT / "process-flow.html"


@pytest.fixture(scope="module")
def html():
    return INDEX.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def checkin_block(html):
    '''Just the Check In tab markup.'''
    start = html.index('id="tab-checkin"')
    end = html.index('id="tab-checkout"')
    return html[start:end]


# ---------------------------------------------------------------- structure


def test_required_files_exist():
    for f in (INDEX, PROCESS_FLOW, ROOT / "FBI_Logo.FlameONLY.png", ROOT / "server.js"):
        assert f.exists(), f"{f.name} is missing"


def test_inline_javascript_parses():
    '''The app is one file; a syntax error takes the whole thing down.'''
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")
    scripts = re.findall(r"<script(?![^>]*\ssrc=)[^>]*>(.*?)</script>",
                         INDEX.read_text(encoding="utf-8"), re.S)
    assert scripts, "no inline script found in index.html"
    with tempfile.TemporaryDirectory() as td:
        js = Path(td) / "bundle.js"
        js.write_text("\n".join(scripts), encoding="utf-8")
        r = subprocess.run([node, "--check", str(js)], capture_output=True, text=True)
    assert r.returncode == 0, f"inline JS has a syntax error:\n{r.stderr}"


# ------------------------------------------------------- check-in behaviour
# Grant, 2026-09-25: this reverses Rev P's "nothing is required". Description,
# Sent From and Checked In By are now mandatory, the detail panel is always open
# rather than collapsed, and the part number is still assigned rather than typed.


REQUIRED_CHECKIN_FIELDS = (
    ("ci-desc", "Description"),
    ("ci-from", "Sent From"),
    ("ci-by", "Checked In By"),
)


def test_required_checkin_fields_are_marked(checkin_block):
    """Each mandatory field carries the asterisk the rest of the app uses."""
    for field_id, label in REQUIRED_CHECKIN_FIELDS:
        assert f'<label for="{field_id}">{label} *</label>' in checkin_block, (
            f"{label} lost its required marker"
        )


def test_required_checkin_fields_are_enforced(html):
    """A marker with no validation behind it is worse than no marker."""
    assert _function_body(html, "validateRequired"), "validateRequired is gone"
    submit = html[html.index("// ---- CHECK IN ----"):html.index("// ---- CHECK OUT ----")]
    assert "validateRequired([" in submit, "check-in submit no longer validates"
    for field_id, label in REQUIRED_CHECKIN_FIELDS:
        assert f"getElementById('{field_id}')" in submit, f"{label} is not validated"


def test_detail_panel_is_not_collapsed(html, checkin_block):
    """Grant asked for the extra fields to be visible, not behind a toggle."""
    assert "detail-toggle" not in html, "the collapse toggle came back"
    assert "detail-heading" in checkin_block, "the detail section lost its heading"
    assert ".detail-body{display:block" in html, "the detail panel is hidden again"


def test_part_number_is_assigned_not_typed(checkin_block):
    field = re.search(r'<input[^>]*id="ci-partnum"[^>]*>', checkin_block)
    assert field, "ci-partnum field is gone"
    assert "readonly" in field.group(0), "part number must stay locked"


def test_auto_numbering_functions_present(html):
    for fn in ("function parsePartNumber", "function nextPartNumber", "function fillNextPartNumber"):
        assert fn in html, f"{fn} is missing; auto part numbering is broken"


def test_only_checkins_drive_the_next_number(html):
    '''Regression: a CHECK OUT once hijacked the prefix of the next assigned number.'''
    body = _function_body(html, "nextPartNumber")
    assert "l.action==='CHECKIN'" in body.replace(" ", ""), (
        "nextPartNumber must filter the log to CHECK IN rows only"
    )


def test_detail_panel_lives_in_the_main_card(checkin_block):
    assert "detail-section" in checkin_block, "the 'Add more detail' section is missing"
    assert "detail-card" not in checkin_block, (
        "detail panel is back in its own card; it belongs inside the main check-in card"
    )


# ------------------------------------------------------------- null safety
# Blank check-in fields are stored as empty strings, but Firebase drops keys whose
# value is null, so these readers must never call a string method on a bare field.


@pytest.mark.parametrize("expr", [
    "p.partNumber.toLowerCase()",
    "p.description.toLowerCase()",
    "p.sentFrom.toLowerCase()",
    "p.checkedInBy.toLowerCase()",
    "l.partNumber.toLowerCase()",
    "l.description.toLowerCase()",
    "l.user.toLowerCase()",
])
def test_no_unguarded_string_calls(html, expr):
    assert expr not in html, f"unguarded {expr} will throw on a blank field; wrap it in (x||'')"


# ------------------------------------------------------------------ hosting
# GitHub Pages is the only host. The Netlify site was deleted 2026-08-19 after the
# two copies drifted; nothing should point at it again.


def test_single_host(html):
    combined = html + PROCESS_FLOW.read_text(encoding="utf-8")
    assert "netlify" not in combined.lower(), "Netlify is retired; GitHub Pages is the only host"


def test_firebase_points_at_the_real_database(html):
    assert "foutsbros-quarantine-default-rtdb" in html, "Firebase database URL changed"


# ----------------------------------------------------------------- helpers


def _strip_prose(block):
    '''Drop visible copy so the word "required" in a hint sentence is not a hit.'''
    block = re.sub(r"<p[^>]*>.*?</p>", "", block, flags=re.S)
    return re.sub(r'placeholder="[^"]*"', "", block)


def _function_body(html, name):
    i = html.index(f"function {name}(")
    depth, start = 0, html.index("{", i)
    for j in range(start, len(html)):
        if html[j] == "{":
            depth += 1
        elif html[j] == "}":
            depth -= 1
            if depth == 0:
                return html[start:j + 1]
    raise AssertionError(f"could not parse body of {name}")


# ------------------------------------------------- save failures stay visible


def test_no_swallowed_save(html):
    '''A rejected write was discarded, so a check-in could look saved and never persist.'''
    assert "fbRef.set(DB).catch(()=>{})" not in html


def test_save_surfaces_rejections(html):
    body = _function_body(html, "saveToServer")
    assert ".catch(" in body
    assert "showSaveAlert(" in body
    assert "showToast(" in body


def test_save_watchdog_covers_a_stalled_write(html):
    '''A promise that never settles is as invisible as one that rejects.'''
    body = _function_body(html, "saveToServer")
    assert "_saveWatchdog" in body


def test_save_alert_banner_is_present(html):
    assert 'id="save-alert"' in html
    assert 'role="alert"' in html
    for fn in ("showSaveAlert", "clearSaveAlert", "retrySave"):
        assert f"function {fn}(" in html


def test_restore_uses_the_guarded_save(html):
    body = _function_body(html, "restoreData")
    assert "saveToServer()" in body
    assert "fbRef.set(" not in body


def test_save_alert_is_hidden_when_printing(html):
    assert ".save-alert{display:none!important}" in html


# ------------------------------------------------- locations (Cage / Warehouse)
# Grant, 2026-09-25: the four numbered zones became two named locations. The
# underlying field is still `shelf`, so existing backups keep restoring.


def test_locations_are_cage_and_warehouse(html):
    assert "const LOCATIONS=['Cage','Warehouse'];" in html, (
        "LOCATIONS is the single source of truth for the two locations"
    )


def test_no_numbered_zones_remain(html):
    assert "Zone" not in html, "a 'Zone' label survived the rename"
    assert "i<=4" not in html, "a hardcoded 1-4 zone loop survived"


def test_location_sort_is_textual(html):
    '''Sorting parsed shelf as an int, which collapses both names to 0.'''
    assert "parseInt(a.shelf)" not in html, "location sort is still numeric"


def test_location_search_matches_the_name(html):
    assert "('zone '+p.shelf)" not in html, "search still looks for the word zone"
    assert "(p.shelf||'').toLowerCase().includes(f)" in html, (
        "search must match the location name"
    )


def test_heatmap_is_built_from_locations(html):
    assert "heatEl.children.length!==LOCATIONS.length" in html, (
        "the heatmap still assumes a fixed cell count"
    )
