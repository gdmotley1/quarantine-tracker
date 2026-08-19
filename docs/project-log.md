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
