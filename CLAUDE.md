# quarantine-tracker

Internal web app for tracking customer-supplied parts at the Fouts Bros plant. A part
arrives from Ryder, Penske, Enterprise, U-Haul, Hertz or Budget, sits in a taped-off
location until its truck is ready, then gets pulled for production. This app is the
traceability record for that gap.

**Audience:** Dawn and the warehouse floor, on a station in the shop. Not office staff,
not a reporting tool. Assume the person using it has gloves on and is in a hurry.

## The rule that outranks everything

**Check-in captures who, what and where. Grant set this on 2026-09-25, reversing the
earlier "nothing is required" rule.** Description, Sent From and Checked In By are
required. The part number is still assigned automatically and locked, and SO# and
Location stay optional. The extra fields are visible by default, not collapsed behind a
toggle. Do not make one of those fields optional again, or re-hide the detail panel,
without asking Grant first. The gate enforces both.

The history matters if you are tempted to "simplify" this back: Rev P deliberately made
check-in require nothing, on the theory that a part logged with only a zone beats a part
not logged at all. Grant reversed it. Do not re-litigate it from the old comments.

Check-OUT requires SO#, the name of who pulled it, who it is Delivered To, and the
Business Unit (Grant, 2026-10-01). Pulling a part is the moment traceability actually
matters. Serial # is optional. `BUSINESS_UNITS` (FIRE, VAN, STC, FCV) near the top of
the script builds the dropdown, the same way `LOCATIONS` does.

## Key commands

```bash
python -m pytest tests/ -q    # the gate. Run before saying anything is done.
```

```bash
git push                       # this is the entire deploy. GitHub Pages, ~1 min.
```

Live: https://gdmotley1.github.io/quarantine-tracker/

## Things that will bite you

**Deploys look like they failed when they did not.** GitHub's CDN serves the old file
for a minute or two after a successful build. Confirm with
`gh api repos/gdmotley1/quarantine-tracker/pages/builds/latest` and add a cache-buster
query string when fetching the page. Do not re-push because a curl looked stale.

**There is exactly one host, on purpose.** A Netlify copy served this app in parallel for
months and the two drifted. It was deleted 2026-08-19. Never add a second host.

**Blank fields must be saved as empty strings, never null.** Firebase drops keys whose
value is null, so a null field comes back as `undefined` and any `.toLowerCase()` on it
throws. The search filters do exactly that. The gate guards the known ones.

**"Location" is stored in a field named `shelf`.** Renaming it would break every
existing backup file on restore. The UI says Location, the data says shelf. Leave it.

**The locations are New Warehouse, Cage, Small Parts and Other** (Grant, 2026-10-02,
replacing Cage and Warehouse, which replaced zones 1-4). `LOCATIONS` near the top of
the script is the single source of truth: the check-in dropdown and the dashboard
heatmap both build from it, so adding one is a one-line change. Older backups hold
"Warehouse" or "1" to "4"; they still restore and display whatever string they carry.

**Aging bands live in `WARN_DAYS` and `CRIT_DAYS`** (30 and 60, Grant 2026-10-02; were
7 and 14). Badges, filters, KPIs, the aging chart and the on-screen labels all read
them. Never write a day threshold as a literal number; the gate fails if you do.

**Sales Order fields show a fixed "SO-"** and people type only the number. Store with
`soValue()`, which adds the prefix once and strips one typed by hand. Messages print the
stored value as is, never `'SO '+salesOrder` (that doubled it once, in Rev M).

**A box of identical parts is many records shown as one line** (Grant, 2026-10-02).
Check-in Quantity creates one part per copy, tagged with `batchId`. List screens go
through `groupByBox()`, and notes and stage changes through `partAndBoxmates()`, or a
box shows 50 rows or changes only one copy. See decisions.md.

**Testing against the live app writes to production Firebase.** There is one database
and no staging. Stub the write first (`fbRef.set = () => Promise.resolve()`) before
exercising check-in, or you will put junk in front of the warehouse. Wait for `_fbReady`
before `fbRef.off()`: anonymous sign-in attaches the live listener late, and detaching
before it lands lets production rows leak into your test copy.

## Layout

```
quarantine-tracker/
  CLAUDE.md          <- you are here, always loaded
  index.html         <- the entire app: markup, CSS and inline JS in one file
  process-flow.html  <- the swim-lane diagram of the physical process
  server.js          <- static file server for local work only
  memory/            <- durable truth. decisions.md is @-imported.
  docs/              <- handoffs/ for workstreams, project-log.md for history
  tests/             <- pytest, the gate. Parses index.html.
  backup-*.json      <- data snapshots, gitignored. This repo is public.
```

The app is deliberately one file. It is small enough that a single file is easier for
Grant to read and edit than a build step, and there is no bundler. Keep it that way
unless there is a reason not to.

## Detailed reference

@memory/decisions.md
