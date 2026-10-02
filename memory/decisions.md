# Decision Log

Permanent decisions, recorded so they are not re-litigated in a future session.
Each entry states the decision, **Why**, and **How to apply**.

Write one the first time a real call is made. A decision that lives only in a chat
transcript is a decision that gets quietly re-made, differently, three weeks later.

## Check-in captures who, what and where (2026-09-25, reverses Rev P)

Description, Sent From and Checked In By are required on check-in. The part number is
still auto-assigned and locked. SO# and Location stay optional. Condition, Damage Notes
and Notes are optional and sit in an "Additional Detail" section that is always open,
inside the main check-in card, not collapsed behind a toggle.

**Why:** Grant's call. Rev P (2026-08-19) made every check-in field optional on the
theory that a part logged with only a zone beats a part not logged at all. Grant
reversed it: a record with no description, sender or name does not trace anything.
Check-out still requires SO# and a name, because pulling a part is when traceability
matters most.

**How to apply:** do not make Description, Sent From or Checked In By optional again,
and do not re-collapse the detail section, without asking Grant first. Do not
re-litigate this from Rev P's old comments or commit messages.
`test_required_checkin_fields_are_marked`, `test_required_checkin_fields_are_enforced`
and `test_detail_panel_is_not_collapsed` guard it.

## Check-out records where the part went (2026-10-01)

Check-out requires Sales Order #, Checked Out By, Delivered To (free text, a person) and
Business Unit (dropdown: FIRE, VAN, STC, FCV, from `BUSINESS_UNITS`). Serial # is
optional. All of them are stored on the CHECK OUT log row, because the part record is
deleted on check-out.

**Why:** Grant's call. Check-out is when traceability matters, and "who pulled it" did
not say who received it or which part of the business it went to. Business Unit is a
fixed list, not free text, so the log stays consistent enough to filter and count.

**How to apply:** add or rename a unit in `BUSINESS_UNITS` only, never in the markup.
Ask Grant before making Delivered To or Business Unit optional. The `test_checkout_*`
tests guard all of it.

## A box of identical parts is N parts that display as one (2026-10-02)

Check-in has a Quantity field (default 1, max `MAX_BOX_QTY` = 200). A quantity over 1
creates that many part records with consecutive numbers (CSP-012 to CSP-021), each
tagged `batchId` (the first number), `batchSeq` and `batchSize`, plus one CHECK IN log
row per copy. Active Quarantine, the check-out dropdown and the location popup show one
line per box ("4 of 6"). Checking out a box pulls its lowest-numbered remaining copy,
and the serial is recorded against that copy. Notes and stage changes on a box apply to
every remaining copy.

**Why:** Grant's call. Boxes of decals or Geotabs are interchangeable: at install time
the floor grabs any one and records its serial. Checking in 50 by hand is not going to
happen, and one record with a quantity would leave check-out pulling the whole box.
Grant picked consecutive numbers over suffixes (CSP-012-01) because the auto-numbering
already handles them, and one line per box over 50 identical rows.

**How to apply:** KPIs, the heatmap and the volume chart count copies, not boxes, so a
box of 50 is 50 parts in Total Active. Any new screen that lists parts should go through
`groupByBox()`, and any action that changes a part should go through
`partAndBoxmates()`. Records without a `batchId` (everything before this date) are
single parts. `test_box_logic_runs_correctly` runs the real functions in node.

## Aging bands, locations and the SO- prefix (2026-10-02)

Three calls from Grant on the same day:

- **Aging:** OK under 30 days, Warning 30 to 59, Critical 60+ (was 7 and 14). Set in
  `WARN_DAYS` and `CRIT_DAYS`; every badge, filter, KPI, chart and label reads them.
- **Locations:** New Warehouse, Cage, Small Parts, Other (was Cage, Warehouse). "New
  Warehouse" is a place name, confirmed with Grant, not "the new list".
- **Sales Order:** both SO fields show a fixed "SO-" and people type only the number,
  so every stored SO has the same shape. A typed "SO-" is stripped so it is never
  doubled.

**Why:** customer parts can wait months for their truck, so 7/14-day alarms were noise.
The locations match the plant. The SO prefix standardises the field for the floor.

**How to apply:** change the bands or locations only in their constants. Store SO through
`soValue()`. The gate fails on a literal day threshold, a stale band label, a missing
SO- prefix, or a doubled one.

## Blank fields are stored as empty strings, never null (2026-08-19)

**Why:** Firebase Realtime Database drops any key whose value is null. A field written
as null comes back `undefined` on the next load, and the active/log search filters call
`.toLowerCase()` on those fields directly, so the whole table throws. This was found
while making check-in optional, before it reached the floor.

**How to apply:** when adding a field, write `''` for blank, and guard every reader as
`(x||'')`. The gate asserts the known readers stay guarded, and
`test_blank_sales_order_is_an_empty_string` covers Sales Order #, which was still
written as null until 2026-10-01.

## Part numbers are assigned from the last CHECK IN only (2026-08-19)

`nextPartNumber()` takes the most recent **check-in**, keeps its prefix and zero-padding,
and increments. It scans every number ever recorded under that prefix, including
checked-out ones, so a number is never reused.

**Why:** the first version keyed off the newest log row of any kind. The newest row was a
check-OUT of a Hertz part, so a Ryder check-in was assigned a Hertz-prefixed number.
Prefixes carry customer meaning, so that was a real mislabel, not a cosmetic bug.

**How to apply:** keep the `action==='CHECK IN'` filter. `test_only_checkins_drive_the_next_number` guards it.

## GitHub Pages is the only host (2026-08-19)

The Netlify site `foutsbros-quarantine.netlify.app` was deleted. `git push` is the
entire deploy.

**Why:** hosting officially moved to Pages in April 2026 (commit 7db9d3e) but the Netlify
site was never shut off, so two live copies of a plant-floor tool ran in parallel for
months and could drift. Two sources of truth for where a physical part is sitting is a
data-integrity hazard, not just clutter.

**How to apply:** never add a second host. `test_single_host` fails if anything in the
app references Netlify again. Note that Pages' CDN serves a stale file for a minute or
two after a build, so verify with the Pages API rather than re-pushing.

## OPEN, not yet decided: what the part-number prefix means

The seed data used customer prefixes (`DCL-RY` Ryder, `DCL-PK` Penske, `DCL-EN`
Enterprise, `DCL-UH` U-Haul, `DCL-HZ` Hertz, `DCL-BG` Budget). Auto-assignment inherits
the prefix from the last part checked in, so a Hertz part logged after a Ryder part gets
a Ryder number. Since the database was cleared for the pilot there is no history, so the
first part in will be `CSP-001` and the pilot inherits whatever that establishes.

Options on the table: accept the number as a meaningless serial, add a customer picker
to the main box that drives the prefix, or hand-seed the first number. **Ask Grant before
building any of them.**
