# Map: Skill Library — a browsable, filterable view of every available skill

Label: `wayfinder:map`
Tracker: local markdown. Tickets live in `docs/tickets/NNN-slug.md`.

## Destination

A decision-complete spec for a read-only local web app that indexes every skill available to Eli
(personal + plugin) from a generated snapshot file, and lets him filter by category, source,
usage recency, and orchestration status — so he can see what he has, what he has forgotten,
what is worth sharing with the team, and what needs refinement.

Done when every open question below is decided and the spec can be handed to `/design-sprint`
or `/feature-sprint` to build. This map decides; it does not build.

## Notes

- Domain: local developer tooling over the `~/.claude` filesystem. Read-only with respect to
  skill files — the tool never edits a `SKILL.md`.
- Skills every session should consult: `/grilling`, `/data-modeling`. `/prototype` for the UI ticket.
  `/research` for the AFK tickets.
- Standing preferences: Ponytail ladder applies — fewest files, no new dependency that can be
  avoided, deletion over addition. Prefer one static HTML page reading one JSON file over a
  framework app, unless a ticket proves otherwise.
- Eli's communication style: Smart Brevity. No em dashes in delivered copy.

### Decisions already locked (from the charting session, 2026-08-18)

These were settled before the map existed and are not tickets.

1. **Read-only.** The tool surfaces state; it never writes to a `SKILL.md`.
2. **Scope: personal + plugin skills, source-filtered.** All ~1362 skills indexed, but the
   Source facet (global / plugin / repo) defaults to Eli's ~172 only.
3. **Data path: snapshot JSON.** A scan script writes `skills.json`; the UI only ever reads that
   file. Same code path serves local and published. Chosen so publishing later is not a rewrite.
4. **Category comes from a one-time LLM pass into a sidecar file**, not from skill frontmatter.
   Re-runnable when skills are added. Keeps skills untouched.
5. **Version / author / last-updated display as "unknown" where absent.** No backfill, no
   fabricated data. Real history starts accumulating from today forward.
6. **Out of the box the app is local.** Publishing is a later step on the same architecture,
   gated by ticket 007.

### Ground truth measured on disk

Two rounds. The charting-session numbers below were substantially **wrong** and are kept only
where corrected numbers confirm them. Tickets 002 and 004 re-measured everything.

**Final inventory (tickets 002, 004, reconciled and re-measured by 005):**

- The library is **426 entries, not 1362 and not 428.** The 988 plugin `SKILL.md` files with no
  marketplace path segment live under `plugins/cache/<marketplace>/<plugin>/<version>/` — the cache
  retains every previously installed version (5 PostHog, 5 Figma, 3 Superpowers, 2 Vercel). 678 of
  the 988 are stale duplicates.
- `~/.claude/skills` has **173 directories but 167 real skills.** Five are `*-workspace` scaffolding,
  one is `.git`.
- Live plugin skills: **257.** The 259-versus-239 conflict was resolved by 005: both were wrong,
  because a recursive `installPath/**/SKILL.md` walk over-collects 29 non-skills (23 vendored
  `skills/<name>/upstream/` copies in the two Vercel plugins, 4 from a nested `plugins/caveman/skills/`
  repo copy, 2 figma `workflow-skills/`). The enumeration rule is **exactly one level:
  `installPath/skills/*/SKILL.md`**, and the same rule is required for the global root. Rows are
  files, not names — 232 distinct plugin names exist, and the 25 that collide across `vercel` and
  `vercel-plugin` are both enabled and both invocable.
- Plus 2 repo-only skills in `~/Development/claude-skills` (`algorithmic-art`, `reflect`).
- `designer-skills` (91), `pm-skills` (55), and `ponytail` (12) are **catalog only** — never
  installed, not enabled — so they are excluded from the library.

**Metadata coverage (ticket 004):**

- Frontmatter across the 167: `metadata.version` on 51, `metadata.author` on 3, `metadata.tags` on 1.
  No `category` field anywhere. (Confirmed.)
- **`author` is derivable for 343 of 428**, not 3. Live plugins declare `author.name` in `plugin.json`
  (12 of 13). And `~/.agents/.skill-lock.json` holds one record per symlinked skill — 84 of the 167
  global skills — carrying `source` (GitHub owner/repo), `sourceUrl`, and a real `updatedAt`.
  Owners: `coreyhaines31/marketingskills` (49), `mattpocock/skills` (34), `remotion-dev/skills` (1).
  Residual 85 default to Eli, flagged `author_source: assumed`.
- **The "no last-modified date exists" finding is partly overturned.** `.skill-lock.json`'s `updatedAt`
  values are genuine per-skill timestamps for 84 skills — the only real ones on the machine. Git is
  still worthless (`~/.claude/skills` and `~/Development/claude-skills` are the same repo, 5 commits,
  one human author). File mtimes are still bulk-copy stamps.
- Frontmatter parsing: PyYAML 6.0.3 is available, no new dependency. Regex loses decisively — it fails
  outright on only 2 files but **silently returns the wrong description on 606** (block scalars
  `description: |` / `>` where it captures the sigil). Recommended hybrid (YAML + force-quote repair)
  measured 1375 clean / 21 repaired / 3 fallback out of 1399.

**Usage signal (ticket 002) — the charting numbers were a severe undercount:**

- **`~/.claude/history.jsonl` is the primary source, not transcripts.** 5,402 records spanning
  **167 days** (Mar 4 to Aug 18), never cleaned.
- **Transcripts are on a proven rolling 30-day whole-file delete.** Hard mtime cutoff at 29 days,
  nothing beyond. So a transcript-derived zero can never mean "never used".
- Magnitude of the undercount: `prime` 18 Skill tool calls vs **146 typed**; `execute` 3 vs 92;
  `feature-sprint` 3 vs 76.
- **Six injection paths found, three recoverable.** Skill tool calls (178, 37 real skills after
  normalizing), hook injection (**3,794 injections across 39 skills, 32 with no other signal at all**
  — `nextjs` alone has 396 injections and 0 tool calls), and `history.jsonl`. Unrecoverable:
  `SubagentStart` bootstrap (verified live, leaves zero trace, zero `isSidechain` records),
  `SessionStart` seen-skills state (per-session temp files deleted at SessionEnd).
- **Free-text name matching is fatal and rejected.** All 167 personal skill names appear as free text
  in at least one transcript because of the system-prompt skill roster; 123 skills with zero real
  signal still match. Structured extraction only.
- **Honest coverage: 44 of 167 personal skills have any recoverable evidence.** Across all 410
  distinct names, 88 covered and 322 with no signal. Four in five skills have no evidence, so the UI
  must distinguish absence of evidence from evidence of absence.
- Scan cost: full parse 1.34s, substring-prefiltered 0.42s. **Build no incremental scanner.** Do
  prefilter before `json.loads`, and dedupe injection payloads by `(file, line, canonical_json)` —
  nested escaping inflates raw counts 2.7x.

## Decisions so far

<!-- one line per closed ticket -->

- [001 — Category taxonomy](tickets/001-category-taxonomy.md) — Two independent facets, not one flat
  list. **Domain** (8 values, nullable meaning `Any`/universal, one primary + optional display-only
  secondary) and **Kind** (7 values, required, single, precedence-tiebroken with Orchestrator first).
  Vendor skills get Domain=Platform / Kind=Reference by rule, no LLM call; only Eli's ~172 get the
  pass. A hand-maintained overrides file corrects wrong calls. "Procurement" was a typo, dropped.
- [002 — Usage contract](tickets/002-usage-contract.md) — `history.jsonl` (167 days, never cleaned) is
  the primary usage source; transcripts are secondary and on a 30-day rolling delete. Three-state rule:
  `used` (count>0), `never_used` (count 0 **and** `coverage=="full_history"`), `no_data` (count 0 and
  `coverage=="transcripts_only"`). Structured extraction only — free-text name matching rejected as
  fatal. No incremental scanner. Snapshot must carry `unrecoverable_paths` and `orphan_usage`.
- [004 — Entry identity](tickets/004-entry-identity.md) — Key is the absolute directory path; display
  `id` is `<name>` / `<plugin>:<name>` / `repo:<name>`. Bare name collides on 96 names / 206 files, and
  frontmatter `name` disagrees with dirname on 8, so neither is safe. Do **not** walk
  `~/.claude/plugins` — enumerate `installPath` from `installed_plugins.json` gated on `enabledPlugins`,
  which drops stale cache and catalog-only marketplaces for free. Global copy is authoritative over the
  repo copy (same git repo; global is newer in all 8 diffs); carry `repo_differs` as a drift signal.
  Exclusions are path-prefix rules, not "no top-level SKILL.md". PyYAML + force-quote repair for parsing.
- [003 — Orchestration rule](tickets/003-orchestration-rule.md) — No cheap rule clears a
  stamp-it-unreviewed bar. Best rule is `degree >= 2 AND (frontmatter orchestrat|sequenc|sub-skill OR
  refs across 2+ Step/Phase sections)`: **precision 0.71, recall 0.86**, flags 17 of 1357. Ship
  architecture instead: `degree >= 2` alone has perfect sample recall and surfaces only **46 files**, so
  the scanner generates candidates mechanically and **one batched LLM call** adjudicates those 46 into
  `orchestrator` / `router` / `leaf`. Name vocabulary **must include `~/.claude/commands`** (3 of
  `feature-sprint`'s 5 targets are commands). Footer-stripping is load-bearing — `pm-skills` stamps a
  Dependencies footer on every leaf, inflating ~30 leaves to 4 refs each. **The inverse relation is the
  stronger field:** 30 skills are called by an orchestrator and call nobody; it exactly recovers the 4
  skills `design-sprint` hand-labelled "orphan skills, do not run ad hoc", and 27 of the 30 have zero
  recorded invocations. Mechanical graph fields live in `skills.json`; only the adjudication goes in the
  sidecar.

- [005 — Snapshot schema and scan contract](tickets/005-snapshot-schema.md) — Three files, merged in
  order: `data/skills.json` (scanner, every run), `data/sidecar.json` (one batched LLM call: domain,
  kind, orchestration adjudication), `data/overrides.json` (hand, last). All three key on `id`, which
  **corrects 003's name-keyed override map** — bare name collides on 96 names. Population re-measured
  at **426 entries** via a strict one-level glob. Python 3 plus PyYAML, one file, no incremental
  scanner. **Bodies are never inlined** — the prior 42-skill snapshot is 819 KB because it carries
  `body` plus a duplicate `fullContent`, which extrapolates to ~8 MB at 426 entries. `version` and
  `updated_at` become `null` rather than the string `"unknown"`, so the recency sort works. A skill
  missing from the sidecar shows `category_status: "uncategorized"` and never fails the scan. New
  fields beyond 001–004: `schema_version`, `scan_errors`, `command_vocabulary`, `category_source`,
  `category_status`, `orchestration_verdict`/`_class`/`_source`, `delegates_to_ids`,
  `delegates_to_unresolved`, `usage.attribution`, `usage.attribution_candidates`, `publishable`.
  **Ambiguous usage counts are written to every candidate entry and flagged**, because hook injections
  carry the bare name while tool calls carry the prefix — so library-wide usage totals must never be
  summed. The prior `~/Development/claude-skills` snapshot and `index.html` are **retired, not
  extended**, but stand as proof the static-page stack works at 781 dependency-free lines.

- [006 — The library UI and its stack](tickets/006-ui-shape.md) — One static HTML file plus
  `skills.json`, no build step, no framework, no design system dependency (Untitled UI rejected: React
  + Tailwind means a bundler and `node_modules`, and breaks both `open <file>.html` and publishing as
  an Artifact unchanged). Direction C, field guide. Default view is Source=Yours, no other filter,
  sorted most-neglected first, with a proven `never_used` ranking as maximally neglected and `no_data`
  ranking last. Four always-visible selects (From, Domain, Kind, Role) plus search; no filter drawer.
  Search covers descriptions by default. A Domain selection keeps the 19 null-domain `Any` skills in
  view, except under Platform. Rows carry Kind, and expanding shows category provenance because both
  Domain/Kind and the orchestration verdict are machine guesses. Cross-filter delegation targets render
  muted and clicking one widens the Source filter; they never vanish, because a dropped edge makes an
  orchestrator look like a leaf. **Closing Q12 exposed a scanner defect:** `SLASH_REF` has no
  left-context guard and no URL awareness, so URL path segments (`/checkout`, `/pricing`) match Eli's
  short generic skill names. Blanking path-like code spans and adding boundary guards takes edges from
  391 to 156, degree >= 2 candidates from 71 to 25, and cross-source edges from 54 to 7, with every
  known real orchestrator intact.
  **Amended same day with an app shell:** a persistent left nav rail, filters moved from a top row
  into a left column (revising Q2 — a column is more always-visible than a row and lifts the
  four-selects-fit-one-line ceiling), search across the top of the results area, and a list/grid view
  toggle. The sketch's `Analysis` and `History` nav items are dropped as out of scope by the map's own
  line, and `History` is unbuildable — no per-skill version history exists yet. The rail ships with
  `Skills` as its only entry.
  **Amended 2026-08-18, second pass:** the rail ships three entries, not one. `Analysis` was built
  as the domain-and-kind coverage grid. `History` was built too, but it is **not** the item this
  ticket rejected: the rejected one was per-skill version history, which still does not exist and
  still cannot be faked. What shipped is Wayfinder's own release history, rendered as a vertical
  timeline: `scan.py` reads the **annotated tags** of its own repo, taking the tag subject as the
  headline, the tag body as the note, and the commits between two tags as the release. A
  hand-written `data/releases.json` mapping shas to prose was built first and then deleted — an
  annotated tag already carries a subject, a body and a date, so the file was the same writing
  plus the bookkeeping, and it could drift out of step with the log. The headline stays curated
  because a commit subject is written for the next developer and this page is not. Commits after
  the newest tag are grouped as Unreleased rather than dropped, on 008's principle that the page
  shows what it has not yet classified. Absent git or an absent `.git` yields an empty timeline
  and a scan error, never a traceback (007's portability rule).
  **Also amended:** the `Record` usage radio group is gone from the filter column. The four usage
  bands became a horizontal tab strip above the results, a strict superset of what the radios
  offered — it splits `used` into gone-quiet and in-rotation, which the radios could not express —
  replacing four stacked card sections that put "In rotation" a full screen below the fold. Two
  controls over one field could contradict each other, so only one survives. The strip sits above
  both the table and the card layout, because the radios served both.
- [007 — Publish allowlist](tickets/007-publish-allowlist.md) — Allowlist only, fail closed, as
  `publishable: true` per `id` in `overrides.json` (not the sidecar, which an LLM refresh would silently
  reset; not frontmatter, which read-only forbids). A crude six-word regex already flags 33 of Eli's 169
  descriptions as carrying personal or client vocabulary, which is a floor — a blocklist fails open every
  time it is wrong. Plugin skills are never published, dropping 257 of 426 before the allowlist is
  consulted. Stripped even for allowlisted entries: the whole `usage` object, absolute paths, `author`
  where `author_source` is `assumed`, local drift fields, and the `roots`/`usage_sources`/`orphan_usage`/
  `scan_errors` envelope. Delegation edges filter to the published set and leave a
  `delegates_to_withheld` count rather than naming private targets. A second command writes a separate
  `public.json`; UI-side hiding is not an option, because a static JSON file next to the page is one
  view-source away.
  **Amended same day:** the sharing model is tool distribution, not snapshot publishing — teammates
  get `scan.py` and the HTML file and run them against their own `~/.claude`. The allowlist and
  `public.json` are specified and deferred, not built. The live hazard inverts: generated `data/*.json`
  must never ship with the tool, an empty first-run state is required, and portability becomes a
  requirement — `REPO_ROOT` is Eli-specific, and every input (plugins, `.skill-lock.json`,
  `history.jsonl`) must be allowed to be missing.
- [008 — Refresh ritual](tickets/008-refresh-ritual.md) — Manual `python3 scan.py`. `SessionEnd` hook
  rejected (1.34s and a failure surface on every session for a weekly tool), cron rejected (sleeping
  laptop, silent stop), on-open rejected as structurally impossible — 006's static page has no server.
  Two cadences: the cheap scan every run, the LLM pass on demand only, its scope just Eli's 169 for
  category and the 25 orchestration candidates. Orphaned sidecar keys are kept and counted, never pruned.
  A new skill appears immediately as `category_status: "uncategorized"` with an Uncategorized filter
  option. The UI renders snapshot age with three states: quiet, warned at 14 days, and at 30 days a note
  that usage coverage is degrading because transcripts roll off at 30. First build ships the honesty,
  not the automation; the trigger to revisit is annoyance, not a date.

- [009 — "Needs work" as a signal](tickets/009-needs-work.md) — The fourth question the README
  promises, unspecified until 005 gave it a schema to sit on. No single cheap rule exists, so 003's
  two-tier architecture is reused verbatim. **Tier one** is four mechanical checks stated as fact,
  flagging **24 of Eli's 169**: `frontmatter_repaired` (16), `name_mismatch` (7, including a
  directory that misspells Karpathy), `missing_target` (1), `foreign_marker` (1). **Tier two** is 43
  suggestive hits — thin bodies and descriptions with no trigger phrasing — adjudicated by one
  batched LLM call, the same shape and size as 003's 46 orchestration candidates. Union is 64 of 169,
  a workable list where the 121-skill `never_used` band is not. Rejected with numbers: dead relative
  paths (103 of 169, the 006 Q12 failure again), naive drive-letter matching (48, because `s://`
  matches inside `https://`), body length as quality, duplicate descriptions (exactly one pair,
  a non-problem), and never-used-and-unreachable (97, which is just the `never_used` band restated).
  Plugin skills are excluded before any check runs: the MAP puts improving them out of scope, and an
  unactionable defect list is noise. Flags go in `skills.json`, the adjudicated verdict in the
  sidecar, overrides win — 005's split, for 005's reason. **Answered during the build and worth
  keeping:** `frontmatter_repaired` is untidy, not broken. Raw PyYAML fails on `design-sprint`,
  `design-accelerator`, `intentional-buy` and `feature-sprint`, and all four appear in the harness's
  own skill roster with their descriptions intact, so Claude Code's loader is the more tolerant of
  the two. No severity tiers were built, because no flag means the skill cannot load. **Built the
  same day:** flags and candidate pool in `scan.py`, Condition facet, row chips, panel sentences,
  rail count. The adjudication pass is specified and not run, on 008's cadence.

- **[010 — The visual system] (2026-08-18, no ticket file; the record is `DESIGN.md`)** — The
  editorial world the first build shipped (Young Serif display, Manrope, Roboto Mono, indigo and
  clay, 999px pills, a 34px serif headline over 13px rows) is **retired**. It was chosen for a
  field guide; what the tool is actually used for is recall, so the world is now a records
  workspace at CRM density, benchmarked against Attio and written down in `DESIGN.md`:
  Schibsted Grotesk for every UI role, JetBrains Mono for anything that is a value, a warm-neutral
  canvas / surface / panel tonal order, hairlines instead of cards, 6px control radii, 34px rows,
  30px controls, one workspace blue that only means current, selected or focused, plus clay for
  never-called and green for in-rotation. `PRODUCT.md` records the product truth the world serves.
  What did **not** change: every scanner contract, every number, the read-only rule, the one-file
  no-dependency stack, and the page's information architecture.
  **006 Q2 is reaffirmed, not reversed.** Facets stay in a left column. What changed is their
  dress: options are 24px selectable rows in the register's own language rather than bare native
  radios, and a facet with more than five options still collapses to a select.
  Two mechanical consequences worth keeping: the register now scrolls inside its own wrapper below
  an 860px minimum table width, so the page body never scrolls sideways and the rail and header
  stay put; and the row's name cell is a flex cell, so a long name ellipses while the `needs work`
  and `orchestrator` chips stay whole. The third chip, `reached only via`, was dropped from the
  register — it is already legible in the Calls column and stated in full in the panel.
  Deliberate and flagged by the mechanical detector: register type runs 11 / 12 / 13px with no
  scale ratio. At 34px rows weight and colour carry the hierarchy; the real scale contrast lives
  in the 24px view title and the 17px panel headline.

- **[011 — Authorship replaces origin] (2026-08-19, no ticket file)** — The register's `From`
  column is **retired**, and with it `ORIGIN()`. Measured, it restated the author: for all 13
  plugin origins the author is a pure function of the plugin slug, and in the one bucket where it
  is not — the 167 global entries — `yours` was false for 87 of them, which are vendored
  third-party skills (`mattpocock/skills` 34, `coreyhaines31/marketingskills` 49) living in the
  global directory. One `Author` column now carries a 16px identity mark plus the display name,
  sorted by name. Nothing is lost: the plugin slug is still in the panel's `Lives at` path, and
  `source` survives as a facet, retitled **Where** (Your directory / Plugins / This repo /
  Everywhere) because location and authorship are different questions and were sharing a word.
  Marks are inline monochrome SVG keyed on a slug derived from the display name, with an initials
  monogram fallback — 9 drawn, 8 monogrammed of 17 identities. Rejected: brand colors (DESIGN.md
  reserves color for current-state), GitHub avatar URLs and favicons (constraint 3, the page must
  be correct offline), data-URI photos in the payload (page weight against `prune()`'s 22%), and
  an author-keyed table in `overrides.json` (that file is id-keyed and merged per entry, so
  display-only data would have cost scanner plumbing and payload bytes; the map sits in the
  template beside `FLAG` and `BANDS` instead). PostHog's hedgehog, Sentry's arc and Sanity's
  letterform were drawn, reviewed at 4× and cut — a wrong-but-close logo is worse than initials.
  **Two 006 defaults are reversed.** The register no longer opens on Source=Yours; `F.source`
  defaults to `all`, `dirty()` compares against `all`, and the band strip leads with `All` instead
  of appending it. Opening on 426 is only correct *because* Author exists — before it, everything
  outside your directory was labelled `yours` and widening the default would have widened a lie.
  **What did not reverse:** the strip still opens on `never_used` (006, `KEY.age`). All is the
  widest scope, not the default; opening on everything would delete the tool's headline claim.
  **Amendment, same day:** authorship is also a facet, sixth in the register, sitting next to
  Where. 17 options is past `OPEN_MAX`, so it collapses to a select on its own. It filters on the
  identity slug rather than the raw author string, which is what keeps Vercel and Vercel Labs
  separable and makes `mattpocock/skills` filter as Matt Pocock. The coverage-cell drill-through
  clears it along with the other filters: a cell answers "what is in here?", and a surviving
  author filter would make the cell's count disagree with the rows it opens.

- [010 — Reach](tickets/010-reach.md) — The permission model does not exist: 2 entries of 426
  declare `allowed-tools`, so the unit is instructed behaviour, not requested permission. Seven
  text-and-filesystem checks, 111 of 426 entries flagged, every label phrased as "contains" and
  never as a verdict. No score, ever. Runs on all 426 including plugin skills, unlike health
  flags, because "stop using it" is an available action. Tier-two adjudication is specified and
  deliberately unbuilt: it would live in the gitignored sidecar and so would not travel.
- [011 — Duplicates](tickets/011-duplicates.md) — Group on the id with the plugin prefix stripped:
  27 groups, 54 entries, 12 byte-identical. Fuzzy matching not built, because cross-name
  similarity found nothing name matching missed. The recommendation names the single deciding
  criterion and refuses to pick when nothing separates two copies. No delete: `file://` cannot
  write, and for 25 of 27 groups deletion is the wrong fix anyway since both files belong to
  enabled plugins and an update restores them. The Resolve dialog copies the command instead.
- [012 — Workflow](tickets/012-workflow-flow.md) — Idea 4's node-link graph became a Workflow
  section: the skill's own Step headings, in document order, with the skills each step calls under
  it. Nothing is inferred and nothing is ordered by the tool. HTML and CSS, not SVG, because once
  the order comes from the file there is no layout to compute. Cycles are stated on the row rather
  than drawn; 5 of 10 orchestrators sit in one, so falling back to the flat list would have
  degraded half the feature. Gated on `orchestration_verdict`, so 10 of 426 entries carry `steps`.
  Idea 5's factual half was already shipped as `Calls` / `Called by`; idea 6 was demoted after
  007's amendment retired its premise. Also fixed `step_section_spread()`, which ended a step at
  its own first subheading and dropped a real target on `launch-sprint`: verdict-neutral, 10
  orchestrators before and after, 0 field diffs across the 426.
- [014 — Handoff and example](tickets/014-handoff-and-example.md) — Settles roadmap ideas 7, 8 and
  9. Idea 9's image half has no source, so what ships is the skill's own `Example` or `Usage`
  section, verbatim, capped at 18 lines: 39 of 426 entries have one, a literal string and so a
  fact, no LLM pass. A looser `usage\b` prefix rule matched 44 and pulled in policy sections, and
  the block is labelled "Example" in Wayfinder's words, so the tight rule wins even though it
  loses three probable examples. Ideas 7 and 8 both become clipboard handoffs over 011's existing
  `toClipboard()`: a note textarea that emits a revision prompt, and a fork prompt carrying the
  closure. `data/notes.json` was not built, because getting text out of a `file://` page is copy
  and paste either way. `scan.py fork` was **refused**, closing the gap decision 1 left open:
  writing a new skill directory breaks no source of truth, but it makes the next scan index
  something Wayfinder wrote, and then every count on the page is partly a measurement of the tool.
  The `/skill-creator` button was dropped outright, not deferred.

## Not yet specified

- **Starting real version history for the skills.** Finding: no per-skill history exists. Making
  it exist from now on (committing `~/.claude/skills` properly, or a version-bump ritual) is
  in scope for the effort but is a separate practice from the library UI, and it is unclear
  whether it belongs to this tool at all. The `History` rail entry does **not** answer this: it
  tracks Wayfinder's own releases, not any skill's.
- **Whether slash commands in `~/.claude/commands` belong in the library as rows.** Partly settled by
  003: commands **must** be in the scanner's name vocabulary regardless, or the orchestration graph is
  wrong. Whether they also get their own library rows is still open. 004 measured them at 11 files, 9
  with frontmatter, no directory, no resources, no Skill-tool usage records, only 2 of 24 schema fields
  populating, and recommends leaving them out as rows. Not yet a decision.
- **The ~14 built-in skills are unreachable by filesystem scan.** `design`, `dataviz`,
  `artifact-design`, `artifact-capabilities`, `security-review`, `simplify`, `loop`, `schedule`, `run`
  and others exist in none of the scanned roots — they ship inside the harness. They are real skills
  Eli can use, several already show usage, and the library will silently omit them. No known way to
  enumerate them short of hardcoding a list.
- **What to do with the 55 `pm-skills`.** Their `marketplace.json` already carries per-skill `category`
  and `tags`, so if they were ever installed, category would be free for them — no LLM pass. Currently
  catalog-only and excluded.
- **How to surface usage that is structurally unrecoverable.** `SubagentStart` bootstrap injection
  leaves no trace at all, and 55% of hook matches are considered but never delivered. Both mean real
  usage the tool cannot see. Whether the UI should say so, and how, is unspecified.

## Handoff

All nine tickets are closed. The spec is decision-complete and ready for `/feature-sprint`.

Known work the build inherits, none of it reopening a decision:

1. **Fix `SLASH_REF` in `scan.py`** per 006's Q12 resolution — blank path-like code spans, add the
   boundary-guarded pattern. Regenerate `skills.json` and the sidecar's orchestration adjudication
   afterwards, since candidate count drops from 71 to 25.
2. **App shell** per 006's layout amendment — nav rail with one entry, left filter column, top search,
   list/grid toggle.
3. **Header elements** per 008 — snapshot age with three threshold states, uncategorized count.
4. **Add an Uncategorized option to the Kind control** (008).
5. **Make it run on someone else's machine** per 007's amendment — `REPO_ROOT` optional, every input
   allowed to be missing, empty first-run state, generated `data/*.json` excluded from distribution.

All five are done. Items 1 to 4 shipped with their tickets. Item 5 closed 2026-08-24, and the
last piece of it was the one nobody had checked: with zero entries the page rendered the
*no-filter-match* state, "Nothing in the guide matches that / No skill fits those filters / Start
over", which is the wrong sentence and the wrong offer for a teammate whose scan came back empty.
There is now a `firstRun()` state that names the roots and lists `scan_errors`, which the UI
payload carries for the first time; `colophon()` and `thesis()` return early rather than print a
paragraph of zeros, because a page of zeros reads as a finding. Also in the same pass: `REPO_ROOT`
became `--repo`, keeping its old value as the default so the 426 / 2-repo numbers every ticket
asserts do not move, and the PyYAML guard stopped telling other people's machines that PyYAML is
already installed on them.

Specified and deliberately not built: the publish path (`public.json`, the allowlist, the field
denylist). It is 007's resolution verbatim, waiting on someone wanting to publish Eli's own library.

**`test_scan.py` exists as of 2026-08-24.** 74 tests, standard library `unittest`, no new
dependency. The split is the decision worth recording: the `Invariant*` classes build fixtures in
a temp directory and pin the *rules* — one-level glob, exclusion prefixes, id shape, the
force-quote repair, 006 Q12's reference guards, 002's three usage states, `prune()` keeping zero —
and pass anywhere. `LiveLibrary` pins the *counts* the tickets assert and skips itself unless
`data/skills.json` matches the 426-entry library, because asserting one person's inventory
unconditionally hands every teammate a red suite on a correct scan, which is the same mistake as
reading a blank usage record as a zero. One finding while writing them, measured and left alone:
006 Q12's `(?![/.])` guard also suppresses a sentence-final `/name.`, which occurs in 5 files and
is a self-reference in all 5, so it costs zero real edges. Pinned as a test rather than fixed.

- [013 — How the sidecar gets written](tickets/013-categorize-command.md) — Nothing produced
  `data/sidecar.json`. Five tickets routed their inferred fields through "one batched LLM pass"
  and no code path wrote the file, so 169 of 426 entries read `uncategorized`, the Domain facet
  carried 2 of 8 options, Kind carried 2 of 7, and the Analysis view scored nothing with a rail
  count of `0`. Resolved as `scan.py --categorize`, which writes `data/categorize.md` and hands
  it to a model outside the tool — the only shape that works with no API key on a teammate's
  machine. One file, four sections, descriptions and computed fields and paths but **never
  bodies**, and it emits only what the sidecar has not already answered. Sections 1 to 3 were
  run: `uncategorized` 0, all 8 domains and all 7 kinds populated, the 22 mechanical
  orchestration candidates split 11 orchestrator / 5 router / 6 leaf, the coverage grid scoring
  143 entries across 49 cells. Section 4, reach, needs 85 files opened and was deliberately not
  run; the panel says so rather than hiding it.
  **Amended 2026-08-24, after the pass was re-run on a second machine.** The prompt's output
  shape is the union of every section's fields, and a model answering section 1 volunteers
  `orchestration_class` for section 1's ids: 35 non-candidates arrived classed, 32 of them
  `leaf` but two `orchestrator` and one `router`, which is the model promoting entries the
  mechanical rule never nominated. `merge_categories()` now gates the `llm` source on
  `orchestration_degree >= 2`, which is 003's architecture stated in code rather than assumed,
  and counts the discards instead of pruning them. The `override` source is never gated, because
  a hand-written correction is meant to win. The prompt now says the shape is not a form.
  **Also measured:** `TRIGGER` matches `when\b`, so it misses **`whenever`** — the most common
  phrasing in the library. Six of the 43 health nominations are strongly-triggered skills caught
  only by that gap, which is why tier two answers "false positive" on 19 of the 43. The regex was
  left alone: it nominates and never flags, so a loose nomination costs one sentence and a tight
  one would lose real cases.
  Tier two corrected the mechanical verdict twice
  (`weekly` and `wayfinder` are leaves) and caught two posthog edges that matched the English
  words "pricing" and "signup" — 006 Q12's lesson surviving into a second layer. Rejected:
  calling an API from `scan.py`, shipping the pass as a harness-bound skill, a rule-based
  classifier, and cutting Domain and Kind from v1.

## Out of scope

- Editing, creating, or version-bumping skills from inside the tool. Read-only was chosen
  deliberately; the tool hands over a file path instead. 014 tested this against the one case with
  a real workflow behind it — forking an orchestrator — and kept the exclusion: the tool would then
  be indexing its own output. Creating is now excluded on an argument, not only by omission.
- Any cloud or team sync service.
- Analytics dashboards, charts, or trend lines over skill usage. A recency column is not a
  charting product. The exclusion covers measurements plotted over time or aggregated across
  entries; one entry's own step structure, read from its own file, is not a measurement, which is
  why 012's Workflow section does not reverse this.
- Maintaining or improving plugin skills. They are indexed for discovery only.
