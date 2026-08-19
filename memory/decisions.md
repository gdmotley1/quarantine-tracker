# Decision Log

Permanent decisions, recorded so they are not re-litigated in a future session.
Each entry states the decision, **Why**, and **How to apply**.

Write one the first time a real call is made. A decision that lives only in a chat
transcript is a decision that gets quietly re-made, differently, three weeks later.

## Check-in requires nothing (2026-08-19, Rev P)

Every field on the check-in form is optional. The part number is auto-assigned and
locked; SO# and Zone sit in the main box; Description, Sent From, Checked In By,
Condition, Damage Notes and Notes live in a collapsed "Add more detail" panel inside
the same card.

**Why:** Grant's call, for the floor. A required field on a warehouse station is not a
data-quality control, it is a reason to skip logging the part entirely. A record with
only a zone still tells you where the part is, which is the whole point of the app.
Check-out is deliberately the opposite and still requires SO# and a name, because
pulling a part is when traceability actually matters.

**How to apply:** never add `required` to a check-in field without asking Grant.
`tests/test_smoke.py::test_checkin_requires_nothing` fails if one appears.

## Blank fields are stored as empty strings, never null (2026-08-19)

**Why:** Firebase Realtime Database drops any key whose value is null. A field written
as null comes back `undefined` on the next load, and the active/log search filters call
`.toLowerCase()` on those fields directly, so the whole table throws. This was found
while making check-in optional, before it reached the floor.

**How to apply:** when adding a field, write `''` for blank, and guard every reader as
`(x||'')`. The gate asserts the known readers stay guarded.

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
