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


# ------------------------------------------------------ check-out serial number
# Grant, 2026-10-01: check-out takes an optional Serial #. The part record is deleted
# on check-out, so the serial is stored only on the CHECK OUT log row.


@pytest.fixture(scope="module")
def checkout_block(html):
    start = html.index('id="tab-checkout"')
    return html[start:html.index("<!-- NOTES THREAD FOR SELECTED PART -->", start)]


def test_checkout_serial_is_optional(checkout_block):
    field = re.search(r'<input[^>]*id="co-serial"[^>]*>', checkout_block)
    assert field, "the Serial # field is missing from check-out"
    assert "required" not in field.group(0), "Serial # is optional on check-out"
    assert '<label for="co-serial">Serial # *' not in checkout_block, "Serial # lost its optional tag"


def test_checkout_serial_reaches_the_log(html):
    submit = html[html.index("// ---- CHECK OUT ----"):html.index("// ---- SEARCH ----")]
    assert "getElementById('co-serial').value.trim();" in submit, (
        "a blank serial must be stored as '', never null"
    )
    assert "serialNumber," in submit, "the CHECK OUT log row no longer records the serial"


def test_checkout_serial_is_shown_searched_and_exported(html):
    assert 'data-sort="serialNumber">Serial #</th>' in html, "the log table lost its Serial # column"
    assert "esc(l.serialNumber||'-')" in html, "the log table cell must guard a missing serial"
    assert "(l.serialNumber||'').toLowerCase().includes(f)" in html, "log search ignores the serial"
    assert "'Serial Number'" in html and "l.serialNumber||''" in html, "the log CSV dropped the serial"


REQUIRED_CHECKOUT_FIELDS = (
    ("co-so", "Sales Order #"),
    ("co-by", "Checked Out By"),
    ("co-to", "Delivered To"),
    ("co-bu", "Business Unit"),
)


def test_required_checkout_fields_are_marked_and_enforced(html, checkout_block):
    """Grant, 2026-10-01: Delivered To and Business Unit joined SO# and name."""
    submit = html[html.index("// ---- CHECK OUT ----"):html.index("// ---- SEARCH ----")]
    for field_id, label in REQUIRED_CHECKOUT_FIELDS:
        assert f'<label for="{field_id}">{label} *</label>' in checkout_block, (
            f"{label} lost its required marker"
        )
        assert f"{{el:document.getElementById('{field_id}'),label:'{label}'}}" in submit, (
            f"{label} is marked required but not validated"
        )


def test_business_units_are_the_single_source(html, checkout_block):
    assert "const BUSINESS_UNITS=['FIRE','VAN','STC','FCV'];" in html, (
        "BUSINESS_UNITS is the single source of truth for the check-out dropdown"
    )
    select = re.search(r'<select id="co-bu"[^>]*>(.*?)</select>', checkout_block, re.S)
    assert select, "the Business Unit dropdown is missing"
    assert select.group(1).count("<option") == 1, (
        "business units are hardcoded in the markup; add them to BUSINESS_UNITS instead"
    )
    assert "BUSINESS_UNITS.forEach" in html, "nothing builds the dropdown from BUSINESS_UNITS"


def test_delivery_fields_reach_the_log(html):
    submit = html[html.index("// ---- CHECK OUT ----"):html.index("// ---- SEARCH ----")]
    assert "deliveredTo,businessUnit," in submit, "the CHECK OUT row no longer records the delivery"
    for key in ("deliveredTo", "businessUnit"):
        assert f"esc(l.{key}||'-')" in html, f"the log table does not show {key}"
        assert f"(l.{key}||'').toLowerCase().includes(f)" in html, f"log search ignores {key}"
        assert f"l.{key}||''," in html, f"the log CSV dropped {key}"


def test_sample_data_uses_the_real_business_units():
    script = (ROOT / "scripts" / "make_sample_data.py").read_text(encoding="utf-8")
    declared = re.search(r"const BUSINESS_UNITS=\[([^\]]*)\];", INDEX.read_text(encoding="utf-8"))
    units = set(re.findall(r"'([^']+)'", declared.group(1)))
    used = set(re.findall(r'"([A-Z]{3,4})"\),', script))
    assert used, "sample check-outs set no business unit"
    assert used <= units, f"sample data uses units the app does not know: {sorted(used - units)}"


def test_movement_log_fits_without_side_scrolling(html):
    """Grant, 2026-10-02: the log scrolled sideways once it reached 15 columns.

    Measured on sample data: all 14 columns fit at 1280px wide only with the log tab
    at full width, wrapping headers, and the time stacked under the date.
    """
    wide = re.search(r"([^{}]*)\{max-width:none\}", html)
    assert wide and ".container:has(#tab-log.active)" in wide.group(1), (
        "the Movement Log is back inside the 1320px page width"
    )
    # Boxes (2026-10-02) added a Qty column to Active Quarantine; same treatment.
    assert ".container:has(#tab-active.active)" in wide.group(1), (
        "Active Quarantine is back inside the 1320px page width"
    )
    for table in ("#log-table", "#active-table"):
        assert f"{table} th" in html and "white-space:normal;vertical-align:bottom" in html, (
            f"{table} headers no longer wrap"
        )
    assert "<th>Time</th>" not in html, "Time is its own column again; it belongs under the date"
    assert 'class="log-time"' in html, "the log row lost the time under the date"


def test_log_table_header_and_row_agree(html):
    """A column added to the header but not the row shifts every cell after it."""
    head = html[html.index('<table id="log-table">'):html.index("</thead>", html.index('<table id="log-table">'))]
    body = _function_body(html, "renderLogTable")
    row = body[body.index("return'<tr>"):]
    row = row[:row.index("</tr>")]
    headers = len(re.findall(r"<th[\s>]", head))  # not <thead>
    assert headers == len(re.findall(r"<td[\s>]", row)), (
        "log table header and row have different column counts"
    )


# ----------------------------------------------------- boxes of identical parts
# Grant, 2026-10-02: a box of identical parts (decals, Geotabs) is checked in once
# with a Quantity. Each copy becomes its own part with a consecutive number, so it can
# be checked out on its own; the screens show one line per box.


def test_quantity_field_is_optional_and_bounded(html, checkin_block):
    field = re.search(r'<input[^>]*id="ci-qty"[^>]*>', checkin_block)
    assert field, "the Quantity field is missing from check-in"
    tag = field.group(0)
    assert 'value="1"' in tag, "Quantity must default to 1 so a single part needs no extra step"
    assert "required" not in tag, "Quantity is not a required field; it defaults to 1"
    cap = re.search(r"const MAX_BOX_QTY=(\d+);", html)
    assert cap and f'max="{cap.group(1)}"' in tag, "the field's max must match MAX_BOX_QTY"


def test_box_checkin_creates_one_record_per_copy(html):
    submit = html[html.index("// ---- CHECK IN ----"):html.index("// ---- CHECK OUT ----")]
    assert "partNumberSeries(nextPartNumber(),qty)" in submit, (
        "box numbers must come from a fresh nextPartNumber, not the display box"
    )
    assert "numbers.forEach((num,i)=>" in submit, "each copy must be its own part record"
    assert "numbers.forEach(num=>appendLog(" in submit, "each copy must get its own CHECK IN row"
    assert "Check In a Box of" in submit, "a box over 1 must be confirmed before it is created"


def test_boxes_show_as_one_line(html):
    for fn in ("renderActiveTable", "populateCheckoutDropdown", "openShelfModal"):
        assert "groupByBox(" in _function_body(html, fn), f"{fn} lists every copy of a box"


def test_box_actions_cover_every_copy(html):
    assert "partAndBoxmates(part)" in _function_body(html, "changeStage"), (
        "a stage change on a box must move every copy"
    )
    assert html.count("notesThread.push(") == 1, (
        "notes must go through addNoteToPart so a box note lands on every copy"
    )
    submit = html[html.index("// ---- CHECK OUT ----"):html.index("// ---- SEARCH ----")]
    assert "resolveCheckoutPart(partId)" in submit, "check-out must resolve a box to one copy"
    assert "batchId:part.batchId||''" in submit, "a check-out row must never write a null batchId"


def test_box_logic_runs_correctly():
    """Run the real box functions in node against a fake database."""
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")
    html = INDEX.read_text(encoding="utf-8")
    fns = "\n".join(
        "function " + n + "(" + html[html.index(f"function {n}(") + len(f"function {n}("):
                                     html.index("{", html.index(f"function {n}("))]
        + _function_body(html, n)
        for n in ("parsePartNumber", "nextPartNumber", "partNumberSeries", "boxRange",
                  "boxCopies", "groupByBox", "partAndBoxmates", "partLabel",
                  "resolveCheckoutPart")
    )
    harness = r"""
const KEYS={parts:'parts',log:'log'};
const DEFAULT_PART_PREFIX='CSP-';
function loadData(k){return DB[k]||[];}
const box=(n,seq)=>({id:'b'+seq,partNumber:'CSP-0'+n,batchId:'CSP-012',batchSeq:seq,batchSize:10,checkinDate:'2026-10-01T10:00:00Z'});
let DB={parts:[
  {id:'s1',partNumber:'CSP-011',batchId:'',checkinDate:'2026-09-30T10:00:00Z'},
  {id:'s0',partNumber:'CSP-005',checkinDate:'2026-09-20T10:00:00Z'},
  box(16,5), box(14,3), box(21,10)
],log:[{action:'CHECK IN',partNumber:'CSP-021',date:'2026-10-01T10:00:00Z'}]};
""" + fns + r"""
const out={};
out.series=partNumberSeries('CSP-012',3);
out.seriesPad=partNumberSeries('CSP-998',3);
out.range=boxRange(DB.parts[2]);
out.next=nextPartNumber();
const g=groupByBox(DB.parts);
out.groups=g.map(x=>[partLabel(x.lead),x.copies.length]);
out.lead=resolveCheckoutPart('box:CSP-012').partNumber;
out.single=resolveCheckoutPart('s1').partNumber;
out.legacy=partAndBoxmates(DB.parts[1]).length;
out.mates=partAndBoxmates(DB.parts[3]).length;
console.log(JSON.stringify(out));
"""
    with tempfile.TemporaryDirectory() as td:
        js = Path(td) / "box.js"
        js.write_text(harness, encoding="utf-8")
        r = subprocess.run([node, str(js)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    import json
    out = json.loads(r.stdout)
    assert out["series"] == ["CSP-012", "CSP-013", "CSP-014"]
    assert out["seriesPad"] == ["CSP-998", "CSP-999", "CSP-1000"]
    assert out["range"] == "CSP-012 – CSP-021", "a box shows its full number range"
    assert out["next"] == "CSP-022", "the next part must land after the whole box"
    assert out["groups"] == [["CSP-011", 1], ["CSP-005", 1], ["CSP-012 – CSP-021", 3]]
    assert out["lead"] == "CSP-014", "checking out a box pulls its lowest-numbered remaining copy"
    assert out["single"] == "CSP-011"
    assert out["legacy"] == 1, "a record with no batchId is not part of any box"
    assert out["mates"] == 3, "a note or stage change on a box reaches every remaining copy"


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


def test_blank_sales_order_is_an_empty_string(html):
    """SO# is optional on check-in, and a blank one was still written as null."""
    assert "getElementById('ci-so').value.trim()||null" not in html, (
        "a blank check-in SO# is written as null; Firebase drops the key"
    )
    assert "salesOrder||null" not in html, "a stage change writes a null salesOrder to the log"


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


def test_locations_are_the_four_named_places(html):
    """Grant, 2026-10-02: New Warehouse, Cage, Small Parts, Other (was Cage, Warehouse)."""
    assert "const LOCATIONS=['New Warehouse','Cage','Small Parts','Other'];" in html, (
        "LOCATIONS is the single source of truth for the locations"
    )
    assert "repeat(2,1fr);gap:.6rem}" not in html.split(".shelf-grid{")[1][:80], (
        "the heatmap grid is fixed at two cells; it must fit however many locations exist"
    )


def test_no_numbered_zones_remain(html):
    assert "Zone" not in html, "a 'Zone' label survived the rename"
    assert "i<=4" not in html, "a hardcoded 1-4 zone loop survived"


# ----------------------------------------------------------------- aging bands
# Grant, 2026-10-02: OK under 30 days, Warning 30-59, Critical 60+ (was 7 and 14).


def test_aging_bands_come_from_one_place(html):
    assert "const WARN_DAYS=30,CRIT_DAYS=60;" in html, "the aging bands moved or changed"
    script = html[html.index("<script>"):]
    stray = re.findall(r"d>=\d+|>=\s*(?:7|14)\b|<14\b", script)
    assert not stray, f"a hardcoded day threshold is back: {stray}; use WARN_DAYS/CRIT_DAYS"
    for word in ("statusClass", "statusLabel"):
        body = _function_body(html, word)
        assert "CRIT_DAYS" in body and "WARN_DAYS" in body, f"{word} ignores the band constants"


def test_aging_labels_are_filled_from_the_constants(html):
    """Fixed text drifted once: the key said 0-6/7-13/14+ after the rules changed."""
    for old in ("0–6 days", "7–13 days", "14+ days", "Critical 14+", "0-6 days", "7-13 days"):
        assert old not in html, f"stale aging label: {old}"
    for el in ("band-ok", "band-warn", "band-crit", "crit-days-label"):
        assert f'id="{el}"' in html and f"set('{el}'," in html, f"{el} is not filled from the constants"


# ---------------------------------------------------------------- sales order
# Grant, 2026-10-02: both SO fields show a fixed "SO-" so people type only the number.


def test_sales_order_fields_show_the_prefix(html):
    for field in ("ci-so", "co-so"):
        wrap = re.search(r'<div class="so-wrap"><span class="so-prefix"[^>]*>SO-</span>'
                         r'<input[^>]*id="' + field + r'"[^>]*></div>', html)
        assert wrap, f"{field} lost its visible SO- prefix"
        assert 'class="so-input"' in wrap.group(0), f"{field} no longer strips a typed SO-"


def test_sales_order_is_stored_with_one_prefix(html):
    """Rev M fixed a doubled 'SO' once; the prefix must be added exactly once."""
    assert "soValue(document.getElementById('ci-so'))" in html, "check-in stores the raw SO box"
    assert "soValue(document.getElementById('co-so'))" in html, "check-out stores the raw SO box"
    assert "soField.value=soNumber(p.salesOrder)" in html, "the check-out prefill would show SO-SO-"
    for doubled in ("' to SO '+salesOrder", "(SO: '+salesOrder", "' (SO: '+esc(l.salesOrder)"):
        assert doubled not in html, f"a message would read 'SO SO-...': {doubled}"


def test_sales_order_prefix_logic_runs_correctly():
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")
    html = INDEX.read_text(encoding="utf-8")
    start = html.index("const SO_PREFIX=")
    code = html[start:html.index("document.querySelectorAll('.so-input')", start)]
    cases = ["98765", "SO-98765", "so 98765", "SO#98765", "SO98765", " SO- 98765 ", "", "SO-",
             "SOUTH-1"]
    harness = code + "console.log(JSON.stringify(" + str(cases).replace("'", '"') + \
        ".map(v=>soValue({value:v}))));"
    with tempfile.TemporaryDirectory() as td:
        js = Path(td) / "so.js"
        js.write_text(harness, encoding="utf-8")
        r = subprocess.run([node, str(js)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    import json
    assert json.loads(r.stdout) == [
        "SO-98765", "SO-98765", "SO-98765", "SO-98765", "SO-98765", "SO-98765", "", "",
        "SO-SOUTH-1",
    ]


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


def test_sample_data_uses_the_real_locations():
    """The generator drifted once: it still wrote zones 1-4 after the rename.

    A restored part whose location is not in LOCATIONS shows a raw value in the
    table and is counted by neither heatmap cell, so tie the two together.
    """
    script = (ROOT / "scripts" / "make_sample_data.py").read_text(encoding="utf-8")
    declared = re.search(r"const LOCATIONS=\[([^\]]*)\];", INDEX.read_text(encoding="utf-8"))
    assert declared, "LOCATIONS is missing from index.html"
    locations = set(re.findall(r"'([^']+)'", declared.group(1)))
    used = set(re.findall(r'loc="([^"]*)"', script))
    # COMPLETED tuples carry the location as the fifth string; catch any of them,
    # and any leftover bare "Warehouse" from before the rename.
    used |= set(re.findall(r'^\s*\("CSP-\d+", "[^"]*", "[^"]*", "[^"]*", "([^"]*)"', script, re.M))
    used |= set(re.findall(r'"(Warehouse)"', script))
    stray = used - locations
    assert not stray, f"sample data writes locations the app does not know: {sorted(stray)}"
    assert used, "sample data sets no location at all"


def test_sample_data_fills_the_required_fields():
    """Every sample part should look like one check-in would actually produce."""
    script = (ROOT / "scripts" / "make_sample_data.py").read_text(encoding="utf-8")
    for empty in ('desc=""', 'frm=""', 'by=""'):
        assert empty not in script, (
            f"a sample part leaves {empty} blank; check-in has required it since 2026-09-25"
        )


def test_stages_are_only_the_three_that_exist(html):
    """Staged and Installed were removed; Check Out is terminal.

    The 'Mark as Installed' branch survived that removal for months, complete with
    a QC sign-off and truck ID prompt, unreachable because changeStage is only
    called from a dropdown built off STAGES.
    """
    assert "const STAGES=['Checked In','Escalated','Missing'];" in html, (
        "STAGES is the single source of truth for stages"
    )
    for dead in ("Installed", "Staged", "qcSignOff", "truckId"):
        assert dead not in html, f"dead stage machinery is back: {dead}"


def test_no_dead_unit_number_field(html):
    """Unit # became Sales Order # in Rev L; the log kept stamping an empty unitNumber."""
    assert "unitNumber" not in html, "the dead unitNumber field is back in the audit log"


# ------------------------------------------------------- home screen + icons


def test_every_declared_icon_exists(html):
    """A missing icon file is a silent 404 that leaves a blank home-screen tile."""
    head = html[:html.index("</head>")]
    refs = re.findall(r'<link rel="(?:icon|apple-touch-icon|manifest)"[^>]*href="([^"]+)"', head)
    assert refs, "no icons are declared"
    manifest = ROOT / "site.webmanifest"
    refs += re.findall(r'"src":\s*"([^"]+)"', manifest.read_text(encoding="utf-8"))
    missing = [r for r in refs if not (ROOT / r).exists()]
    assert not missing, f"declared but not in the repo: {missing}"


def test_status_bar_does_not_cover_the_page(html):
    """viewport-fit=cover with a translucent status bar draws the page under it on iOS."""
    if "viewport-fit=cover" not in html:
        return
    assert "env(safe-area-inset-top" in html, (
        "viewport-fit=cover without safe-area padding puts the header under the status bar"
    )


# --------------------------------------------------------------- header + menus


def test_stage_menu_escapes_the_scrolling_table(html):
    """.table-wrap sets overflow-x, which clipped the menu at the section's bottom edge.

    An absolutely positioned menu is cut off by that wrapper; a fixed one is not.
    """
    assert ".stage-dd-menu{position:fixed" in html, (
        "the stage menu is positioned inside the scrolling wrapper again; it will be clipped"
    )
    body = _function_body(html, "toggleStageDropdown")
    assert "getBoundingClientRect" in body, "a fixed menu has to be placed against the badge"
    assert "innerHeight" in body, "the menu must flip above the badge near the bottom of the window"


def test_stage_menu_closes_on_scroll(html):
    """A fixed menu does not travel with the scrolling ancestor it was placed against."""
    assert "window.addEventListener('scroll',closeAllStageDropdowns,true)" in html, (
        "the stage menu must close on scroll, or it detaches from its row"
    )


def test_header_only_offers_print_and_kiosk(html):
    """Grant, 2026-09-25: the floor gets Print and Export CSV, nothing else.

    backupData and restoreData stay in the file on purpose, reachable from the
    console, because they are the only way to pull a full JSON copy of the log.
    """
    header = html[html.index('<div class="header-actions">'):html.index('</header>')]
    assert "backupData()" not in header, "Backup is back in the header"
    assert "restore-input').click()" not in header, "Restore is back in the header"
    assert "printView()" in header, "Print is missing from the header"
    for fn in ("function backupData", "async function restoreData"):
        assert fn in html, f"{fn} was deleted; it is the console-only escape hatch"


def test_tabs_show_no_shortcut_numbers(html):
    """Grant, 2026-10-02: the small 1-5 next to each tab name came off."""
    nav = html[html.index('<nav id="main-nav">'):html.index("</nav>")]
    assert "nav-key" not in html, "the tab shortcut numbers are back"
    assert not re.search(r"</?span", nav), "a tab label carries extra markup again"


def test_export_csv_is_still_offered(html):
    assert html.count("Export CSV") >= 2, "both tables should still export CSV"


def test_tab_change_clears_the_search_boxes(html):
    """Clicking Critical on the dashboard left "critical" in the Active search.

    Coming back to that tab later showed a filtered table with no sign why, which
    reads as an empty quarantine.
    """
    body = _function_body(html, "switchTab")
    assert "search-active" in body and "search-log" in body, (
        "switchTab must clear both search boxes"
    )
    assert "tabName!==_currentTab" in body.replace(" ", ""), (
        "clear on a real tab change only, so clicking the current tab keeps what was typed"
    )


def test_kpi_tiles_preset_the_filter_after_switching(html):
    """The tiles rely on switchTab running first; reversing the order would self-clear."""
    for word in ("critical", "missing"):
        tile = re.search(r'onclick="switchTab\(\'active\'\);[^"]*' + word + r'[^"]*"', html)
        assert tile, f"the {word} tile no longer switches tabs before presetting the search"
        call = tile.group(0)
        assert call.index("switchTab") < call.index("search-active"), (
            f"the {word} tile presets the search before switching tabs; the switch would wipe it"
        )
