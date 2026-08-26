# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

One primary user: Eli, the person whose `~/.claude` the scanner reads. He is fluent in every term
the page uses and knows a fraction of his own library by heart. He opens Skill Library on a laptop
(~1440px, system-driven light or dark) in short sessions between other work, not as a dashboard he
keeps open.

A second audience is planned, not present: a teammate reading a published snapshot
(`public.json`, ticket 007) with none of Eli's context. Terms that only make sense to the author
must still be legible to that reader, so the page explains its own vocabulary rather than
assuming it.

## Product Purpose

Skill Library answers four questions about the skills this machine can reach: what do I have, which
have I forgotten, which are worth sharing, and which need work.

The dominant job in practice is **recall, not lookup**. Eli reaches for the same handful of skills
from memory. He has 426 entries and uses a fraction of them. Success is a session where the page
tells him about a skill he owns and forgot, or one worth improving, and he acts on it. A session
that only confirms what he already knew is a failure of the product, not of the user.

## Positioning

Every input is read-only and already on disk. Skill Library's mechanism is honest evidence about
usage: `history.jsonl` spans 167 days and is never cleaned, transcripts roll off at 30 days, and
two invocation paths leave no trace at all. That is why the product distinguishes three states —
**in use**, **never used** (a full history exists and shows nothing), and **no record** (only the
30-day window was available, so absence proves nothing). No competing view of a skill library can
make the never-used claim truthfully without that distinction.

## Operating Context

- Launched as `python3 scan.py --prototype` then `open index.html`. No server, no build step.
- Read entirely off `file://`. Everything the page needs is inlined into one HTML file.
- Sessions are short and scanning-heavy: many rows, fast search, keyboard over mouse.
- Acting on a finding means leaving the page: Skill Library hands over a filesystem path to open
  elsewhere. It never edits a `SKILL.md`.

## Capabilities and Constraints

- 426 entries: 167 global, 257 plugin, 2 repo. Rows are files, not names.
- Facets: source, domain (7 + universal `Any`), kind (7), role (orchestrator / leaf), condition
  (needs work / clean), usage band (never called / gone quiet / in rotation / all).
- Two record views (table and card), an analysis grid of domain x kind, and a history timeline.
- Domain and kind are inferred by a batched LLM pass into a sidecar; overrides are hand-written
  and win. The page must say inferred values are inferred.
- Read-only with respect to `SKILL.md`, always.
- No build step, no framework, no dependency beyond PyYAML. No ES modules, no external `<script
  src>` or `<link>` for app code, because `file://` blocks them. CSS and JS live inline in
  `index.template.html`. Web fonts from Google Fonts are the one permitted external request, and
  the page must be correct when it fails.
- Generated files never ship: `data/*.json` and `index.html` are gitignored. `data/overrides.json`
  is hand-written and tracked.
- Known gaps stated on the page rather than hidden: ~14 built-in skills are invisible, publishing
  is unbuilt, history is Skill Library's own and not per-skill.

## Brand Commitments

- Name: Skill Library.
- Voice: Smart Brevity. Short declaratives, no em dashes in delivered copy, no hype.
- The page never fabricates a number. Absent data reads as "unknown", never as zero.

## Evidence on Hand

- Real measured inventory and usage numbers in `docs/MAP.md` and `docs/tickets/001-009`.
- Real snapshot data in `data/skills.json`, `data/sidecar.json`, `data/overrides.json`.
- No testimonials, customers, pricing, or benchmarks exist. None may be invented.

## Product Principles

1. **Evidence over inference.** Absence of evidence is displayed as absence of evidence.
2. **Recall is the job.** Surfacing the forgotten outranks confirming the familiar.
3. **Hand over, never edit.** The tool ends at a path.
4. **One page, no dependencies.** Distribution is copying two files.
5. **Say what is inferred.** Domain, kind, and orchestration verdicts carry their provenance.

## Accessibility & Inclusion

Both light and dark themes get equal care; the layout must hold at 1280px. State is never carried
by color alone — every band, flag, and usage state has a text or shape carrier as well.
