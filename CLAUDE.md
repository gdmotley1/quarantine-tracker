# quarantine-tracker

Internal web app for tracking customer-supplied parts at the Fouts Bros plant. A part
arrives from Ryder, Penske, Enterprise, U-Haul, Hertz or Budget, sits in a taped-off
zone until its truck is ready, then gets pulled for production. This app is the
traceability record for that gap.

**Audience:** Dawn and the warehouse floor, on a station in the shop. Not office staff,
not a reporting tool. Assume the person using it has gloves on and is in a hurry.

## The rule that outranks everything

**Check-in stays dead simple, and nothing on it is required.** That is Grant's explicit
call. The part number is assigned automatically and locked; SO# and Zone are optional;
everything else lives in the collapsed "Add more detail" panel. A part that gets logged
with only a zone is a win, because the alternative on a busy floor is not logging it at
all. Do not add a required field to check-in without asking Grant first. The gate
enforces this.

Check-OUT is the opposite and still requires SO# and a name. Pulling a part is the
moment traceability actually matters.

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

**"Zone" is stored in a field named `shelf`.** Renaming it would mean migrating live
records. The UI says Zone, the data says shelf. Leave it.

**Testing against the live app writes to production Firebase.** There is one database
and no staging. Stub the write first (`fbRef.set = () => Promise.resolve()`) before
exercising check-in, or you will put junk in front of the warehouse.

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
