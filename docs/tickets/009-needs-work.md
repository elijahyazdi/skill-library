# 009 — "Needs work" as a signal beyond recency

Parent: `../MAP.md`
Label: `wayfinder:research`
Blocked by: 005 (needed the snapshot schema to exist)
Status: closed 2026-08-18 (see Resolution)

## Question

The MAP promises four questions: what do I have, what have I forgotten, what is worth sharing,
what needs work. The first two ship. The third is 007, specified and deferred. The fourth was
never specified at all, because the MAP could not specify it before the schema existed:

> **"Needs refinement" as a signal beyond recency.** Recency answers "forgotten". It does not
> answer "this skill is thin, or wrong, or was written before I knew better".

The schema exists now. So:

1. What signals of "this skill needs work" are actually present on disk?
2. Which of them are precise enough to state as fact, and which need adjudication?
3. Does this belong to Eli's 169 only, or to all 426?
4. Where does the verdict live, and what does the page do with it?

## Resolution

Status: closed. Measured 2026-08-18 against the live snapshot: 426 entries, of which 169 are Eli's
(167 global, 2 repo).

### Headline

**There is no single cheap rule for "needs work", and the two-tier architecture from 003 applies
verbatim.** Four mechanical checks are precise enough to state as fact and flag **24 of 169**
skills. A wider net of 40 more is suggestive but not decidable without reading the skill, so it
goes to the same batched-LLM adjudication pattern 003 established for orchestration. The union is
**64 of 169**, which is a list a person can work through — unlike the 121 `never_used` band, which
is a description of a library rather than a to-do list.

The trigger to build this was live: `/product-lens` was invoked during the build session and
turned out to be a 378-byte stub whose body points at `D:/tmp/everything-claude-code/...`, a drive
letter that does not exist on this machine. The library indexed it, showed it as a normal skill,
and said nothing.

### Tier one: mechanical, precise, ship as fact

Each is a statement about the file, not a judgment about the writing. No LLM call.

| Flag | Hits | What it means |
| --- | --- | --- |
| `frontmatter_repaired` | 16 | YAML did not parse until the force-quote repair from 004 ran |
| `name_mismatch` | 7 | Frontmatter `name` disagrees with the directory that defines the id |
| `missing_target` | 1 | Delegates to a name that resolves to nothing (`feature-sprint` → `execute`, `prime`) |
| `foreign_marker` | 1 | Windows drive path or CJK text in a library that is otherwise all English |

**24 distinct skills**, one of which carries two flags (`feature-sprint`). All four are already
computed or nearly so: `parse_status` and `delegates_to_unresolved` are in the snapshot today and
rendered nowhere except one line of the detail panel.

`name_mismatch` is the surprise. It is 7 skills and every one is real: six `sanity-*` directories
whose frontmatter drops the vendor prefix, plus **`kaparthy-guidelines`, whose directory misspells
Karpathy** while the frontmatter has it right. 004 measured this at 8 and treated it purely as an
identity hazard. It is also a defect report.

### Tier two: suggestive, needs adjudication

| Signal | Hits | Why it cannot be a fact |
| --- | --- | --- |
| Body under 20 lines | 9 | 8 of the 9 are intentionally short pointers (`grill-me`, `research`, `handoff`) |
| Description carries no trigger phrasing | 40 | Real risk — 002 established the description is what the model reads — but plenty of skills trigger fine without the words "use when" |

**43 skills, 40 of them not already hard-flagged.** Per 003: the scanner generates the pool
mechanically, one batched LLM call adjudicates it, and the verdict lands in the sidecar. The pool
is the same order of magnitude as 003's 46 orchestration candidates, so the cost is known.

### Rules measured and rejected

These are the ones worth not rebuilding later.

- **Dead relative-path references.** Flags **103 of 169**. The regex ate URL path segments and
  `[placeholder]` template tokens — precisely the failure 006 Q12 found in `SLASH_REF`. It could
  be salvaged with the same left-context guard and code-span blanking, but it was not, and the
  103 is the number to beat before anyone tries.
- **Naive drive-letter detection.** A first pass matched `[A-Za-z]:[\\/]` and flagged **48 of
  169**, because `s://` inside every `https://` URL matches. With a boundary guard it flags **1**,
  which is correct. Same lesson, third time: guard the left context.
- **Body length as a quality proxy.** Rejected above. Length is not quality.
- **Duplicate or colliding descriptions.** Measured across all 169 by token Jaccard: **exactly one
  pair** at ≥0.35, `grill-me` / `grill-with-docs`, which are knowingly a pair. This was expected to
  be the sharpest finding and it is a non-problem. Do not build it.
- **"Never used and unreachable by the graph."** Flags **97 of 169**. That is not a defect signal,
  it is the `never_used` band restated with extra steps.

### Scope: Eli's 169 only

Plugin skills are excluded before any check runs. The MAP puts "maintaining or improving plugin
skills" out of scope — they are indexed for discovery. A defect list you cannot act on is noise,
and it would be 257 of 426 rows of it.

### Where the verdict lives

Follows 005 exactly, for the reason 005 gave:

1. `data/skills.json` — `health_flags`, an array of the tier-one flag names. Scanner, every run,
   mechanical, no judgment.
2. `data/sidecar.json` — `health_verdict` for adjudicated entries. One batched call, on demand,
   per 008's two-cadence rule.
3. `data/overrides.json` — wins, per `id`.

The verdict must not go in `skills.json`, and the mechanical flags must not go in the sidecar. An
LLM refresh would silently reset hand corrections, which is why 005 split the files in the first
place.

### UI

- A **Condition** control in the filter column: Any / Flagged / Clean. Three values, so it renders
  as the open radio group the other short facets use.
- Flag chips on the row, the same treatment as the `orchestrator` badge.
- The detail panel spells each flag out in a sentence. The panel's `Notes` line already surfaces
  `frontmatter repaired` and `repo copy has drifted`, so this extends an existing line rather than
  adding a second one.
- The count belongs in the rail next to the uncategorized count, not as a fifth nav entry. This is
  a facet, not a destination.

### Answered during the build: repaired is untidy, not broken

`frontmatter_repaired` does **not** mean the skill is unreadable. Raw `yaml.safe_load` fails on
`design-sprint`, `design-accelerator`, `intentional-buy` and `feature-sprint` with
`mapping values are not allowed here` — and all four appear in the harness's own skill roster with
their full descriptions intact. Claude Code's loader is more tolerant than PyYAML.

So the flag means "this file is not valid YAML and something less forgiving will choke on it",
which is worth knowing and worth fixing, but is not an outage. **No severity tiers were built.**
None of the four flags means the skill cannot load, so sorting them into broken and untidy would
be inventing a distinction the evidence does not support. The chip states a count; the panel
states a sentence per flag; there is no score.

### Open, deliberately

- **Description quality as a first-class signal.** 002 established the description is the trigger
  text, so a weak one is the most consequential defect a skill can have. Detecting weakness is not
  a regex problem, and the 40 no-trigger-phrasing hits are a proxy, not a measurement.

### What to hand to the build

1. Scanner computes `health_flags` for `source in (global, repo)` only. Reuse `parse_status` and
   `delegates_to_unresolved`; add the name comparison and the boundary-guarded marker scan.
2. Scanner emits the tier-two candidate pool the same way it emits `degree >= 2` for 003.
3. Sidecar gains `health_verdict`; `overrides.json` may override it per `id`.
4. UI: Condition facet, row chips, panel sentences, rail count.
5. No severity model. Answered above.

## Built 2026-08-18

Shipped in the same session the ticket was written. `attach_health()` in `scan.py` computes
`health_flags` and `health_candidate` for `source in (global, repo)`; `merge_categories()` merges
`health_verdict` from the sidecar and then overrides, matching the category precedence. The page
gained a Condition facet (Any / Needs work / Clean), a clay `needs work` chip on rows and cards, a
sentence per flag in the detail panel, and the flagged count in the rail beside the uncategorized
one. `Clean` excludes plugin skills rather than counting 257 unscored rows as clean.

Live numbers match the ticket exactly: **24 flagged** (16 / 7 / 1 / 1), **43 candidates**. The
adjudication pass itself is specified and not run — it is the same on-demand LLM cadence as 001 and
003, and 008's rule is that the cheap scan runs every time and the LLM pass runs when asked.
