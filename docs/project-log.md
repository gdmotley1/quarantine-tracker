# quarantine-tracker: project log

History, not instructions. This file is **not** auto-loaded.

Append here: how a conclusion was reached, superseded numbers, build archaeology. Anything
that becomes a standing rule gets promoted to `memory/decisions.md` instead.

New entries at the bottom, with an absolute date.
## 2026-08-19 — Check-in overhaul, single host, pilot reset

**Rev P (`18adf62`).** Check-in fields all made optional, part numbers auto-assigned and
locked, extra fields moved into a collapsed panel. Folded into a single card in `9900054`.
Null-safety hardening across the search filters came along with it, because Firebase drops
null keys and the filters called `.toLowerCase()` on bare fields.

**Two live copies found and resolved.** The app was being served by both GitHub Pages and a
Netlify site that had never been shut off after hosting moved to Pages in April. Netlify
was deleted (`86e9650`). Also deleted a stale April-vintage duplicate working copy at
`claude-code/quarantine-tracker/`, which was 7 revisions behind and had no unique commits.

**Database cleared for the pilot.** 13 seed parts and 25 log rows removed, `logId` reset to
0. Every record was demo data (all part ids prefixed `seed`, fictional user names). Snapshot
kept locally at `backup-before-pilot-2026-08-19.json`, gitignored because this repo is public
and future snapshots will contain real customer data.

**Brought up to the house standard.** Was 7/14 on project-doctor. Added CLAUDE.md,
memory/decisions.md, a real pytest gate that parses index.html, .gitattributes, AGENTS.md,
and deny rules. Untracked `.claude/settings.local.json` and pruned three allow-list entries
that had Supabase JWTs embedded in them.

**Left alone deliberately:** `process-flow.html` Phase 2 is titled "Unit # Requirement".
That looked stale, since the app replaced its Unit # field with Sales Order # in Rev L, but
the doc is describing the *physical* truck unit number that customers write on parts, which
is still real practice. Reframing it is Grant's call, not a bug fix.

## 2026-10-01: Decision log caught up, home-screen icons, SO# null fix

**Decision log was contradicting CLAUDE.md.** `memory/decisions.md` still led with Rev P's
"check-in requires nothing", and pointed at a test that no longer existed, a week after
Grant reversed it on 2026-09-25. Since that file is @-imported every session, it was
actively telling agents the wrong rule. Rewritten to the current one.

**Browser and home-screen icons committed.** Built 2026-09-25 but never committed. The
`black-translucent` status bar plus `viewport-fit=cover` draws the page under the iOS
status bar, so the page is now padded by the safe-area insets and a navy strip fills the
status-bar area. Verified by forcing a 47px inset in a 375px viewport; a real device
was not available. All insets are 0 in an ordinary browser tab, so desktop is unchanged.

**Sales Order # was still written as null** on check-in (when blank) and on stage-change
log rows, against the empty-string rule. Every reader was guarded, so nothing crashed,
but the key silently vanished from Firebase. Now `''`, with a gate test.

## 2026-10-01: Serial # on check-out

Grant asked for an optional Serial # text field on check-out. The part record is deleted
when it is checked out, so the serial is stored only on the CHECK OUT log row
(`serialNumber`, `''` when blank). It shows in the confirm dialog, a new Serial # column in
the Movement Log, the log search and the log CSV. Check-in rows and stage rows carry no
serial, so their cell reads "-". The sample-data generator wrote the dead `unitNumber`
field on its check-out rows; that became `serialNumber`, with two of four left blank.

Testing note: detaching the live listener with `fbRef.off()` right after a reload is not
enough. Anonymous sign-in finishes later and attaches a fresh listener, which pulled
production rows into the in-memory test copy. Writes were stubbed throughout and the
live database was confirmed untouched, but stub after the app has loaded, not before.

## 2026-10-01: Delivered To and Business Unit on check-out

Grant asked for two more mandatory check-out fields: who the part is Delivered To (free
text) and the Business Unit (dropdown). He chose a fixed list over free text, and gave the
units as FIRE, VAN, STC, FCV in caps. The Fouts_AOP cover schema lists Fire, Tow, Service
and Aftermarket, which is a different (planning) taxonomy; do not merge the two. Both
fields ride on the CHECK OUT log row next to Serial #, and show in the confirm dialog, two
new Movement Log columns, the log search and the log CSV. Recorded in decisions.md.

Tested on sample data with the safer order: wait for `_fbReady`, then `fbRef.off()` and
stub `fbRef.set`. Production was re-read afterwards and was untouched.

## 2026-10-02: Movement Log fits without side-scrolling

Grant asked for the log to be wide enough to see every column. With Serial #, Delivered
To and Business Unit added it had 15 columns and needed 1512px inside a 1225px box at a
1920 screen. The log tab now uses the full window width (`.container:has(#tab-log.active)`),
its headers wrap, padding is a little tighter, Description and Notes can shrink to 110px,
and the time sits under the date instead of in its own column. Measured on sample data:
fits at 1920, 1366 and 1280. Below about 1280 it scrolls again; the other tabs keep the
1320px width. The CSV still exports Date and Time as separate columns.

## 2026-10-02: Boxes of identical parts

Grant: shipments of commodities (a box of decals, Geotabs) are interchangeable, and at
install the floor grabs any one and records its serial. Checking in 50 by hand would not
happen. He asked for a quantity on check-in that makes N copies with unique numbers, so
check-out still pulls one at a time. He chose consecutive numbers over a box-plus-suffix
scheme, and one line per box over a row per copy. Design recorded in decisions.md.

Verified on sample data (which now includes a box of 6 Geotabs, 2 already installed):
box check-in of 3 (confirm dialog, 3 records CSP-023 to CSP-025, 3 log rows, folded into
one Recent Activity line, form back to Qty 1), quantity 0 / 201 / 2.5 refused, box
check-out pulled the lowest copy and logged the serial against it, a box note landed on
every copy, and escalating the box moved every copy with one log row each.

The Qty column and box ranges pushed Active Quarantine to 1373px at a 1366 screen, so it
got the Movement Log's full-width treatment, and a box's number range wraps onto two
lines. Both tables now fit at 1280, 1366 and 1920.

## 2026-10-02: Test records cleared from production

After Grant tested the box feature on the live site, the database held only test data:
16 parts and 20 log rows (CSP-001 to CSP-018, including a 15-copy GeoTab box and
placeholder entries like "F" / "V" / "C"). Grant confirmed a full wipe. Backed up first
to `backup-before-cleanup-2026-10-02.json` (gitignored; SHA-256 of parts+log+logId
matched the live data before the reset), then set `app_state` to empty. Next part in is
CSP-001. Restore with `restoreData` from the browser console if ever needed.
