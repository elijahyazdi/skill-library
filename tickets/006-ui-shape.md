# 006 — The library UI, and the stack that carries it

Parent: `../MAP.md`
Label: `wayfinder:prototype` (HITL)
Blocked by: 001, 005
Status: CLOSED 2026-08-18

## Question

What does the library look like, and what is the thinnest thing that renders it?

Make a rough artifact to react to rather than arguing in the abstract. Prototype against the
real snapshot once 005 lands.

Must decide:

1. Primary view: dense sortable table, or card grid? 1362 rows argues table; "browse and
   rediscover" argues cards.
2. Which facets are always visible vs behind a filter drawer: source, category, usage recency,
   orchestration, version-known.
3. What the default view is on open. Proposal to react to: Eli's skills only, sorted by
   least-recently-used, so the tool answers "what have I forgotten" before he touches a control.
4. What a row shows without expanding, and what expanding reveals. Confirm the file path is
   surfaced, since the tool is read-only and handing off to an editor is the action.
5. Stack. Leading candidate on Ponytail grounds: one static HTML file plus `skills.json`, no
   build step, no dependency, opens with `open index.html` and publishes as an Artifact
   unchanged. The prototype should either confirm this holds at 1362 rows or prove it does not.
6. Whether search-by-description is needed, given descriptions are the actual trigger text and
   are long.

## Inherited from 001 (closed)

7. **Does a Domain filter include `Any`-domain skills?** 001 made Domain nullable, where null means
   *universal* rather than *unknown* (`xlsx`, `grilling`, `agent-browser` genuinely serve every
   domain). So filtering Domain=Marketing could legitimately include the `Any` skills alongside the
   Marketing ones, or show them only under their own `Any` view. Deciding this here, with a
   prototype in front of you, rather than in the abstract.
8. **Kind is a first-class facet, not a badge.** The seven Kinds (Orchestrator, Ritual, Converter,
   Reviewer, Generator, Thinking tool, Reference) filter independently of Domain. The "which are
   orchestration skills" question from the original idea is answered by Kind=Orchestrator, so there
   is no separate orchestration badge to design.

## Inherited from 002, 003, 004 (all closed)

9. **The row must show orchestration evidence, not just a badge.** 003's rule runs at precision 0.71.
   Rendering a bare boolean at that rate teaches distrust of the facet within a week. Show `degree` and
   the `delegates_to` list on the row so a wrong call is visibly wrong.
10. **A "never reached on its own" filter, driven by `reached_via`.** 003 argues this is the single
    field most likely to change what Eli does: 30 skills are called only by an orchestrator, 27 of
    which have zero recorded invocations. It answers the forgotten-skills problem more directly than
    recency does.
11. **The three usage states need three visual treatments, not two.** 002 established that only 44 of
    167 personal skills have any recoverable evidence. `no_data` must not read as `never_used`, or the
    tool's headline list is 80% false accusations.
12. **Dangling graph edges across the Source filter.** `style-tiles` delegates to `figma-use`, a plugin
    skill. With Source defaulting to Eli's skills only, a graph or delegates-to view will point at rows
    that are filtered out. Decide whether callees outside the filter resolve, grey out, or vanish.

## Partial resolutions (2026-08-18)

- **Q5 — Stack: decided.** One static HTML file plus `skills.json`, no build step, no framework, no
  design system dependency. Untitled UI was considered and rejected: it is React + Tailwind, which
  would add a bundler, `node_modules`, and a build step to a repo that is currently one Python file
  and one HTML template. It also breaks the two properties the stack was chosen for — opens with
  `open <file>.html`, and publishes as an Artifact unchanged.
  - Guardrail: no component abstraction layer. Semantic HTML plus a small set of CSS custom
    properties for tokens. If the Untitled UI look is wanted later, port its token values into those
    custom properties rather than its code.
- **Q1 — Direction: C (field guide) provisionally.** `ui-c-fieldguide.html` is the working direction.
  Visual treatment is not signed off and can change without reopening 001-005; the data contract is
  what is stable.

- **Q7 — Does a Domain filter include `Any`-domain skills? Yes, with one exception.** Selecting a
  domain keeps the 19 null-domain skills in view, rendered in italic as `Any`, because null means
  universal: hiding `grilling` or `xlsx` from every domain view makes them unfindable, which is the
  exact failure the tool exists to prevent. The exception is **Platform**, which is a provenance
  bucket rather than a kind of work — `xlsx` serves marketing, it does not serve "Platform" — so
  universal skills are excluded there. A separate `Universal only` option filters to the 19 alone.
- **Q6 — Search covers descriptions, on by default.** Descriptions are the trigger text a model
  reads, so name-only search finds strictly less. The `Glosses` toggle turns it off for the cases
  where a long description makes every query match.
- **Q2 (partial) — Domain and Kind are always-visible controls**, sitting alongside From and Role.
  No filter drawer. Four selects and a search box fit one row at the tested widths.
- **Q4 (partial) — the row carries Kind over Domain in one column**, not as a badge beside the name.
  Badges beside the name were built first and rejected: the name cell is capped at 250px, so
  `community-marketing` clipped its own domain chip, and with a domain filter active every row
  repeated the filter back at the reader. Expanding additionally shows the category with its
  provenance (`inferred, correctable`) and, for adjudicated entries, the orchestration class and the
  one-line reason. Provenance is on the row because 001 assigns Domain and Kind by machine and 003
  runs at 0.71 precision; a value that cannot be seen as a guess gets trusted like a fact.

- **Q3 — Default view: your skills, most-neglected first, in the index.** Source=Yours, no domain,
  kind, or usage filter, sorted by Last used descending. The map's proposal survives, but the
  objection raised against it does not: `no_data` was measured at 178 entries library-wide and
  every one of them is a plugin skill. All 169 of Eli's own carry `full_history` coverage, so the
  default view contains no unknowns at all and a recency sort accuses nobody.
  - The prototype exposed a real defect while settling this. `ordered()` ranks null last by design,
    and a `never_used` skill has a null `days_since_last_use`, so sorting by recency buried all 122
    never-used skills at the bottom — the page led with "122 have never once been called" and then
    listed them last. The sort key now treats a proven `never_used` as maximally neglected
    (`Infinity`) while leaving `no_data` null. Never-used first descending, most-recent first
    ascending, unknowns last in both directions. Ties inside the never-used band sort by name;
    there is no recency signal there to order them by.

Inherited item 12 is resolved below.

## Q12 — Dangling graph edges across the Source filter: resolved 2026-08-18

**Decision: cross-filter callees resolve and render, in a muted "outside your filter" state,
and clicking one widens the Source filter to include it rather than navigating to a hidden row.**

Vanishing was rejected outright: a delegates-to list that silently drops targets makes an
orchestrator look like a leaf, which is the single error the graph exists to prevent. Greying out
with no affordance was rejected because the reader's next question is always "what is that thing",
and the answer is one filter widening away.

The cost of this decision is one CSS class and one click handler, because the problem is far
smaller than the ticket assumed. Measuring it exposed a scanner defect that matters more than
the UI question.

### The measurement, and the defect it exposed

Counting resolved, id-deduped edges whose target sits in a different `source` bucket than its
caller: **54 cross-source edges today**. Inspecting them shows most are not references at all.

`SLASH_REF` is `/([a-z][a-z0-9-]*(?::[a-z][a-z0-9-]*)?)\b` with no left-context guard and no
URL awareness, so it fires on any path segment in any prose or code span. Verified examples:

- `posthog:signals-scout-csp-violations` → `signup`, from the line "a critical funnel page
  (`/checkout`, `/signup`, `/login`)".
- `posthog:exploring-autocapture-events` → `pricing`, from a table cell
  `https://app.example.com/pricing`.
- `posthog:signals-scout-anomaly-detection` → `weekly`, and `figma:figma-design-to-code` → `image`.

Eli's short, generic skill names (`ads`, `image`, `schema`, `pricing`, `weekly`, `signup`,
`triage`) collide with ordinary URL vocabulary, so the noise lands almost entirely on the
plugin → global direction: 33 of the 42 cross-source edges the current snapshot carries.

**Fix, specified here and measured, to be applied by whoever builds the scanner.** Blank any
backticked code span that looks like a path or URL (contains `://`, more than one `/`, or a `.`),
then match with boundary guards:

```
TIGHT = r'(?<![\w/.])/([a-z][a-z0-9-]*(?::[a-z][a-z0-9-]*)?)\b(?![/.])'
```

Measured effect over all 426 entries, same counter both sides:

| | resolved id edges | degree >= 2 candidates | cross-source edges |
|---|---|---|---|
| today | 391 | 71 | 54 |
| with the fix | 156 | 25 | 7 |

Known real orchestrators survive intact: `design-sprint` keeps all 8 targets, `feature-sprint` 4,
`pm-orchestrator` 4, `style-tiles` 2.

A stricter variant was tried and **rejected**: gating slash refs on `INVOKE_LINE` the way backtick
refs are gated cuts candidates from 71 to 17 and loses real orchestrators that list `/ux-flow`-style
targets without an invocation verb on the line.

Four of the surviving 7 cross-source edges are still noise (`pricing` twice, `signup`, `humanizer`).
The three real ones are `daily-reflection` → `repo:reflect`, `style-tiles` → `figma:figma-use`, and
`caveman:caveman-review` → `review`. 003's architecture already covers the residue: the mechanical
rule generates candidates and one batched LLM call adjudicates them.

**Downstream:** with 3 real cross-filter edges library-wide, a dedicated graph view is not
warranted. Delegation stays an expanded-row list, as Q4 already had it.

Status: CLOSED 2026-08-18. All questions resolved.

## Amendment — 2026-08-18: app shell layout

Eli sketched a preferred layout after Q12 closed, with the constraint "do not increase scope a
lot". Adopted with one subtraction.

**Adopted — the shell.** A persistent left nav rail (logo at top), and to its right a page with
its title, a **left filter column** replacing the top filter row, a search field across the top
of the results area, and a **view toggle** at top right.

**Revises Q2.** The four facets move from a single always-visible row into the left column. The
"no filter drawer" decision survives and is strengthened: a column is more always-visible than a
row, and it lifts the width ceiling that forced four selects to fit one line. Facet controls can
now be lists with counts rather than selects.

**Revises Q4 in one detail only.** The view toggle offers list and grid over the same rows. The
field-guide row content, the Kind column, and the expanded detail are unchanged.

**Subtracted — the other nav items.** The sketch shows `Analysis` and `History` alongside
`Skills`. Both are out of scope by the map's own line: "Analytics dashboards, charts, or trend
lines over skill usage. A recency column is not a charting product." `History` is additionally
unbuildable today — 004 measured that no per-skill version history exists on this machine, and
005 recorded that real history only starts accumulating forward from now.

So the rail ships with `Skills` as its only entry. The rail is the cheap part; the pages behind
it are not. Adding an entry later is a list item and a route, and nothing in the data contract
blocks it.

**Scope delta: small.** Moving filters from a row to a column and adding a nav rail is CSS grid
plus markup reshuffling in a file that already has no framework. The view toggle is one class
swap on the results container. No new decision, no new data, no new dependency.
