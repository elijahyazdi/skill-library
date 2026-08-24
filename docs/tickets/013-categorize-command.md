# 013 — How the sidecar gets written

Parent: `../MAP.md`
Label: `wayfinder:grilling` (HITL)
Blocked by: 001, 003, 005, 008, 009, 010
Status: closed 2026-08-24, built. Sections 1-3 run; section 4 deliberately not run.

Takes the number `ROADMAP.md` reserved for "Does Wayfinder create files", on 012's precedent:
that ticket has no demand behind it and this one blocks the ship. The reserved question is
restated and renumbered at the bottom. It is not answered here, and this ticket does not touch
it — nothing below writes outside the tool's own directory.

## Question

Five tickets route their inferred fields through "one batched LLM pass into `data/sidecar.json`":
001 (domain, kind), 003 (orchestration class), 009 (health verdict), 010 (reach verdict, deferred),
and 005, which defines the file's shape. Nothing in the repo produces that file. `merge_categories()`
reads it and no code path writes it. There is no prompt, no subcommand, and no documented ritual.

The gap is invisible in the tickets and loud in the product. This ticket decides how the file gets
written, by whom, and what the command that helps looks like.

## Measurement, 2026-08-24, against the live 426-entry snapshot

| Pool | Entries | Source of the number |
|------|---------|----------------------|
| `category_status: uncategorized` | 169 | 167 global + 2 repo. Zero plugins: 001 assigns them by rule |
| Orchestration candidates, `degree >= 2` | 22 | 003's mechanical pool, post-006 Q12 |
| Health tier-two candidates | 43 | 009's suggestive pool, all inside the 169 |
| Reach tier-two, sharp flags only | 85 | 010's `REACH_SHARP`, includes plugins |
| Union of the first three | **177** | 14 of the 22 orchestration candidates are already in the 169 |
| Union of all four | 247 | |

Cost of the first three as one prompt, descriptions only, no bodies:

| | |
|--|--|
| Description characters across the 177 | 85,841 |
| Rough input tokens | ~21,500 |
| Rough output tokens, 30 per entry | ~5,300 |
| Body lines across the 177, if bodies were inlined | 36,828 |

The pass fits in one context with room to spare, and it fits **only** because bodies stay out.

What the missing file costs on the page, measured in the browser:

- Domain facet renders 2 of 8 options: `Platform` and `Universal only`.
- Kind facet renders 2 of 7: `Reference` and `Uncategorized (169)`.
- Analysis rail count reads `0`. The domain-by-kind coverage grid, the whole view, has nothing
  to score: `coverage()` filters on `e.domain && e.domain !== 'Platform' && e.kind`.
- `orchestration_source` is `rule` on all 426. The `orchestrator` / `router` / `leaf` classes 003
  designed have never been populated.
- The header reads "169 uncategorized" on every run, forever.

Two of six facets and one of four views are dead, and the dead half is the half about the skills
the user wrote. `PRODUCT.md` names recall as the job. Domain and kind are the recall surface.

## Resolution

1. **The tool prepares the pass; a model outside the tool performs it.** `scan.py` gains
   `--categorize`, which writes `data/categorize.md`: a prompt, the pools, and the exact output
   shape. The user pastes it into Claude Code or any assistant, and that assistant writes
   `data/sidecar.json`. The next `scan.py --prototype` picks it up.

   This is principle 3, hand over and never edit, applied to the tool's own gap. It is also the
   only shape that travels: teammates get the repo and run it against their own `~/.claude`, so
   the mechanism has to work with no API key, no account, and no network.

2. **One file, four labelled sections, one paste.** The four judgments have different pools and
   different output schemas, but splitting them into four commands means four rituals for a thing
   done every few weeks. Section 4, reach, states that it requires opening 85 files and may be
   skipped; the other three are answerable from what the file already carries.

3. **The prompt carries descriptions and computed fields. Never bodies.** 36,828 lines of body
   across the core pool is the difference between a prompt that fits and one that does not, and
   005 already refuses to inline bodies for the same reason. Each entry carries its `id`,
   `description`, `body_lines`, `delegates_to`, `reached_via`, `health_flags`, `reach_flags`,
   and **its absolute path**. The path is what makes section 4 possible without inlining anything:
   the adjudicator opens the 85 files itself.

4. **`gloss` rides along, per `ROADMAP.md` idea 3.** The shipped first-sentence form in `gloss()`
   stays as the fallback, because the page has to be correct on a machine that never ran the pass.
   A sidecar `gloss` wins when present and is labelled inferred like every other sidecar field.

5. **The emitted pools are the still-unadjudicated ones, not the full pools.** `--categorize` reads
   the existing sidecar first and omits anything already answered, so a re-run after adding four
   skills is a four-entry prompt. The prompt instructs a merge into the existing `entries` map,
   never a replacement. 008's rule holds unchanged: orphaned sidecar keys are kept and counted,
   never pruned.

6. **`--categorize` exits without writing when every pool is empty,** and says so. A command that
   emits an empty prompt is a command that gets pasted anyway.

7. **This does not reopen decision 1 and does not answer the reserved 013.** `scan.py` already
   writes `data/skills.json` and `index.html`. `data/categorize.md` is a fourth file in the same
   directory. Nothing here writes to a `SKILL.md`, and nothing here writes anywhere under
   `~/.claude`, which is the question the reserved ticket actually asks.

## Rejected

**`scan.py` calls an API directly.** Needs an API key on every teammate's machine, a network
call from a tool whose entire premise is reading local disk, and either a new dependency or
hand-rolled `urllib` plus retry plus a cost the user did not agree to. `urllib` is standard
library so constraint 2 survives on a technicality, but the key requirement alone kills it: the
distribution model is copy the repo and run it, and this makes the first run fail with an auth
error.

**Ship the pass as a Claude Code skill inside this repo.** Cleaner ritual, and it is the natural
upgrade path once the prompt stops changing. Rejected for now because it binds the tool to one
harness, adds a `.claude/skills/` directory to a repo whose distribution story is "copy two
files", and the prompt is going to change several times before it is worth freezing. Revisit when
`data/categorize.md` has survived a month unedited.

**A rule-based kind classifier instead of a model.** Tempting, since 001's kinds are fairly
mechanical. Rejected on 003's and 009's shared finding, restated twice already in this repo: no
cheap rule clears a stamp-it-unreviewed bar, and a wrong kind on 169 rows is worse than an honest
`uncategorized`, because the facet would look complete.

**Cut Domain and Kind from v1 and ship the four working facets.** Genuinely viable and cheaper
than this ticket. Rejected because it deletes the Analysis view, and because `category_status`,
`category_source` and the whole sidecar merge would stay in the schema serving nothing. If this
ticket stalls, this is the fallback, and it is a real one.

**Adjudicate reach as its own command.** Deferred rather than rejected. It is the one section
with a cost the others do not have, and if it turns out nobody runs it, it earns its own flag.

## Build order

1. `--categorize`: pool selection, sidecar diff, prompt emission. No page changes.
2. Run it once against the live library. Fix what the prompt gets wrong before writing anything
   about it down.
3. The `gloss` fallback chain in the page, which is one line in `gloss()` plus `gloss` in
   `UI_ENTRY_FIELDS`.
4. `README`, `MAP` and `CLAUDE.md` in the same change, so the record never lags the behavior.

## Verifying

CLAUDE.md's existing list, plus:

- `--categorize` on a library with an empty sidecar emits all four sections, 169 / 22 / 43 / 85.
- Run the pass, rescan. `uncategorized` reads 0, the Domain facet carries all 8 options, the Kind
  facet drops `Uncategorized`, the Analysis rail count is no longer 0, and the coverage grid
  scores. `category_source` reads `llm` on the 169.
- `--categorize` again immediately. Every pool is empty, nothing is written, the command says so.
- Add one skill, rescan, `--categorize`. The prompt carries one entry.
- Hand-edit one id in `data/overrides.json`. Rescan. `category_source` reads `override` on that
  entry and `llm` on its neighbours. 005's precedence is the thing being checked.
- Delete `data/sidecar.json` and rescan. 169 uncategorized, no traceback, page correct. The
  fallback is not optional: it is what every teammate sees on their first run.

## Renumbered

**014 — Does Wayfinder create files.** `ROADMAP.md` reserved 013 for this. Forced by roadmap ideas
6 and 8: bundling writes a `.zip`, forking writes a new skill directory under `~/.claude/skills`.
Decision 1 covers editing existing skills, not creating new ones, and that gap should be closed
deliberately rather than by a button. Still unwritten, still waiting on demand behind idea 6.

## What shipped, 2026-08-24

Built as decided, with three things worth reading before changing any of it.

**`scan.py --categorize` writes `data/categorize.md`.** One file, four labelled sections, and on
the first run it was 163 KB: 169 category, 22 orchestration, 43 health, 85 reach. It carries
descriptions, the step structure the scanner read out of each file's own headings, `delegates_to`,
the flags, and the absolute path. It carries no bodies. Run it again after the pass and it emits
85 reach and nothing else, which is decision 5 working.

**Sections 1 to 3 were answered; section 4 was not.** That is the split the ticket predicted:
the first three are answerable from the emitted file, and reach needs 85 files opened. The page
renders `reach_verdict` when it exists and says "Pattern matches in the file, not a verdict" when
it does not, so nothing about the unrun section is hidden. `test_reach_tier_two_is_still_unrun`
is the test that will tell whoever runs it that it landed.

**The result, measured.** `uncategorized` 169 to **0**. `category_source` is `llm` on 169 and
`rule` on 257. All 8 domains and all 7 kinds populate: Platform 263, Marketing 53, Engineering 28,
Product & Design 21, universal 20, PM & Delivery 15, Personal 11, Writing 10, Business & Clients 5.
The orchestration adjudication split the 22 mechanical candidates into 11 orchestrators, 5 routers
and 6 leaves. The Analysis rail count went from 0 to 19 and the coverage grid now scores 143
entries across 49 cells: 12 strong, 18 thin, 19 gaps.

**Three findings from running it, none of which reopen a decision:**

1. **The adjudication corrected the mechanical verdict twice, which is the whole point of tier
   two.** `weekly` and `wayfinder` both clear `degree >= 2` and are `leaf`: `weekly` reads what
   `daily-reflection` wrote and informs `morning` without running either, and `wayfinder`
   sequences its own tickets rather than skills, naming three as optional consults in a template
   field. Two of the posthog scouts matched only on shared boilerplate, and two matched the
   English words "pricing" and "signup" rather than the skills of those names - the 006 Q12
   lesson surviving into a second layer.
2. **Kind and `orchestration_class` can contradict each other, and the panel prints both four
   lines apart.** The first pass made `ask-matt` and `wayfinder` Kind=Orchestrator while adjudging
   them router and leaf. 001 defines Orchestrator as sequencing other skills, which is the same
   claim the class makes, so the two must agree. Fixed in the sidecar and pinned by
   `test_kind_never_contradicts_the_adjudication`.
3. **The Uncategorized option in the Kind facet is now conditional.** 008 wants it so a new skill
   is reachable the moment it lands, but at 0 it is a control that selects nothing. It renders
   only when the count is non-zero, which satisfies 008 without leaving dead furniture.

**Also shipped:** `gloss` and `reach_verdict` through `merge_categories`, `UI_ENTRY_FIELDS` and
the panel. The gloss chain is sidecar first, the description's first sentence second, and the
panel labels a written gloss "inferred". The colophon now counts glosses alongside domains.

Not shipped and not missed: nothing in `overrides.json`. Two corrections were needed and both
belonged in the sidecar, because the sidecar is where they were wrong.
