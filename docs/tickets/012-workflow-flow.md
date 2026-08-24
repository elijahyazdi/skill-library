# 012 — Drawing an orchestrator's workflow

Parent: `../MAP.md`
Label: `wayfinder:grilling` (HITL)
Blocked by: 003, 006
Status: closed 2026-08-19, built

## Question

`ROADMAP.md` idea 4 proposes drawing the orchestration graph, idea 5 proposes surfacing a
skill's inputs and outputs, and idea 6 proposes copy-and-share with orchestration bundling.
All three were scored **Next**. This ticket decides what, if anything, gets built, and settles
the shape before any code.

The roadmap's framing for idea 4 was a node-link diagram: "inline SVG with a hand-rolled
layered layout, maybe 80 lines of JS", falling back to the flat list when a graph is cyclic.
Measurement below shows every part of that framing is wrong in a way that makes the feature
cheaper, not more expensive.

## Measurement, 2026-08-19, against the live 426-entry snapshot

| Signal | Value |
|--------|-------|
| Entries with `orchestration_verdict` | 10 |
| Direct delegation degree, range | 2–8 |
| Transitive closure size, range | 3–22 nodes |
| Transitive closure depth, range | 1–5 |
| Roots whose closure contains a cycle | 5 of 10 |
| Non-orchestrators carrying `delegates_to` | 61 |
| Entries with non-empty `reached_via` | 27 |
| Orchestrators with `Step`/`Phase` sections in the body | 10 of 10 |
| Step/Phase section count, range | 6–11 |

Two of those rows overturn the roadmap:

**Cycles are not an edge case.** Five of ten roots sit in one, `weekly` at depth 1. The
roadmap's "if a graph turns out to be cyclic, say so and fall back to the list" would degrade
half the feature to the list that already exists.

**Every orchestrator states its own order.** All ten carry 6–11 `Step`/`Phase` headings, and
`step_section_spread()` already walks them for 003's verdict rule. `delegates_to` is
`sorted(...)` — alphabetical — so the document order the authors wrote is being computed and
then discarded. That order is the whole feature.

## Resolution

### 1. Idea 5 is already shipped. Closed, not built.

The roadmap sells idea 5's factual half as derived from usage: "typically called after X,
typically hands off to Y". The `usage` object carries counts, `first_seen_at`, `last_used_at`,
sources and attribution. It carries **no adjacency and no session ordering**. Nothing about
call sequence is derivable from usage.

The only real source for "calls" and "called by" is the static delegation graph, which 003
built and which the entry panel already renders as `Calls` and `Called by`
(`index.template.html:914-916`). The factual half of idea 5 exists.

What remains is the LLM-inferred "best inputs and outputs", which the roadmap itself calls
"a good sidecar field and a bad fact". That is a separate, later ticket. It is not Next.

### 2. Idea 6 is demoted. Its premise was retired by 007.

007's amendment replaced the sharing model: teammates get the tool and the scanner and run
them against their own `~/.claude`. Under that model nobody needs a bundle of Eli's skills,
and `public.json` is specified-and-dormant by design.

Idea 6 only makes sense as a different product move — handing a colleague one orchestrator
plus its dependency closure. Nobody has asked for that. Building a zip exporter for zero
demand fails the first question worth asking about any feature.

Demoted to **Later**. The roadmap's proposed "012 — Does Wayfinder create files" is renumbered
**013**, and again to **014** once 013 went to the categorize pass. It stays unwritten until idea
6 has a demand behind it. If a Copy action falls out of
this ticket's work for free, that is the only sliver worth keeping, and it copies paths to the
clipboard — it does not write.

### 3. Idea 4 becomes a workflow, not a graph.

The panel gains a **Workflow** section for the 10 orchestrators: the skill's own `Step`/`Phase`
headings, in document order, with the skills each step calls listed under it.

This is a different feature from the one the roadmap scored, and a better one. A call graph
answers "what does this reach". A workflow answers "what does this do, in what order", which
is the question a person opening `design-sprint` actually has. It is also strictly more
honest: the rows are literally the file's headings, so nothing is inferred and nothing is
ordered by the tool's convenience.

**Rendered as HTML and CSS, not SVG.** Once the layout is "the file's steps, in order", there
is no layout to compute. An ordered list with a CSS-drawn spine costs no layout math, keeps
text selectable and searchable, gives assistive technology a real list, inherits the existing
tokens, and survives the Google Fonts request failing. SVG here would buy curved edges and
cost all of that. This drops idea 4's cost score from 3 to roughly 1.

Decisions inside the section:

- **Every Step section is drawn, including ones that call no skill.** `design-sprint` has 11
  steps and 8 targets; the steps that are prose-only are still steps. Drawing only the
  delegating ones makes the numbering jump and turns the workflow back into a call graph.
- **Order comes from the Step headings**, with byte offset as the tiebreaker inside a section
  and the fallback where a skill has no headings. `delegates_to` stays sorted exactly as it is
  so nothing downstream shifts.
- **A target named in two steps is drawn in both.** `maintenance-sprint` calls `feature-sprint`
  in Step 4.5 and again in Step 5. The flow is a sequence, not a set; deduplicating would
  misreport the workflow.
- **Targets referenced outside any step get a trailing "Also references" group.**
  `maintenance-sprint` names 2 of 4 outside its steps, `feature-sprint` 3 of 4. Dropping them
  would make a flow showing 2 of 5 targets read as complete.
- **Unresolved targets are drawn**, muted and non-clickable, with the legend naming them.
  `feature-sprint` resolves 2 of 4; omitting the other 2 makes a 4-step workflow look like a
  2-step one. Same rule 007 §3 set for withheld edges: a filtered node must not read as a leaf.
- **Cycles are drawn as a note on the row**, `↺ also references <name>`, not as an edge. A
  back-edge is a fact about the library, not a rendering failure. Drawing a literal arrow back
  up an HTML list is the one thing that would need SVG, and it is not worth reintroducing SVG
  for five entries.
- **Step titles are stripped of backticks and `*` emphasis and ellipsised by CSS.** Raw titles
  read ``Step 2: Current state — run `/ux-flow` `` and `Step 1.5: Grill (presales mode only)`.
  Rendering them verbatim leaks authoring syntax; parsing them properly means an inline
  markdown parser in a file with no dependencies, for cosmetics.
- **Targets are clickable and navigate the panel to that entry.** `links()` renders `<span>`
  today, so this is new behavior. One panel, one root: navigating resets the section to the
  new entry's own workflow. No nested flows, no expansion state carried across navigation.
- **The section sits after the description and before the `<dl>`**, with its own `max-height`
  and internal scroll. `Calls` and `Called by` stay exactly where they are — they are the
  accessible fallback and the copy surface, and anything the section cannot draw is still there.
- **Section heading is "Workflow"**, with one line of provenance underneath: *"The Step
  headings in this skill's file, in order. Names are the skills it calls."* Same pattern 010
  and 011 use for anything derived.

Not built: a whole-library map, in-place expansion of child orchestrators, a graph for the 61
non-orchestrators that carry edges. Each is one predicate away if it earns itself.

### 4. `step_section_spread()` slices steps wrong. Fixed once, at the root.

`SECTION` matches a heading at any level and the slice ends at `marks[i+1]`, the next heading
of **any** level. A `## Step` section therefore ends at its own first `### ` subheading.

`launch-sprint` `## Step 6: Comms` ends at `### Build-in-public post`, where
`Hand off to /marketing-sprint` lives. The target is real, sits in a real step, and the slicer
drops it.

Separately, these files contain headings that are **template output the skill instructs the
agent to write** — `## QA Results — [Product name] — [Date]`, `## Launch log — [Product name]`.
They are indistinguishable from document structure and they terminate step slices early.
`strip_body()` removes fenced blocks and the pm-skills footer but these are not fenced.

The fix, one function, both callers:

- A step section runs until the next heading **at the same or shallower level**.
- A heading whose title contains a `[...]` placeholder is not a section boundary.
- `step_blocks(body, vocab, self_name)` returns `[(title, [refs])]`, and
  `step_section_spread()` becomes `sum(1 for _, refs in step_blocks(...) if refs)`.

`step_blocks()` is the flow's data source and 003's verdict input, one definition of what a
step is. Writing a second slicer for the UI would leave two functions disagreeing about that
in a file whose entire value is that its heuristics are documented and measured.

**Measured impact, patched copy of the scanner run against the same tree:**

| | before | after |
|---|---|---|
| Orchestrators (`orchestration_verdict` true) | 10 | **10** |
| Field diffs across all 426 on `orchestration_verdict`, `orchestration_degree`, `delegates_to`, `reached_via`, `delegates_to_unresolved` | — | **0** |
| `launch-sprint` targets located inside a step | 4 of 5 | **5 of 5** |
| All other nine orchestrators | — | unchanged |

The fix is verdict-neutral. It recovers one target on one entry and it removes a defect that
would have shown up as a hole in the workflow section on the entry most likely to be read. No
figure quoted in `MAP.md`, 003, 010 or 011 moves, so none of them need amending.

Had the count moved, the count would have been accepted and the documents amended. Tuning the
threshold to preserve 10 would be fitting the rule to a number the docs happen to quote.

### 5. Schema and payload

- New `steps` field: `[{title, refs: [name], unresolved: [name]}]`, gated on
  `orchestration_verdict` so only 10 of 426 entries carry it. Anything wider is payload for a
  surface nothing renders, and `prune()` cannot drop it because it would be non-empty.
- Added to `UI_ENTRY_FIELDS`. `SCHEMA_VERSION` 1 → 2.
- **Not** added to the post-`JSON.parse` restore list. The page reads it with a truthiness
  check, which is how CLAUDE.md says almost everything is read; only the three arrays the page
  indexes into directly get restored.

### 6. Listeners

Clickable targets live inside the panel, which `openPanel()` rebuilds via `innerHTML` and
wires inline for `.js-shut` alone — a third wiring site that CLAUDE.md's `wireShell()` /
`wireRows()` split does not mention. Introduce `wirePanel()`, called from `openPanel()` where
`.js-shut` is bound today, and add the third bullet to CLAUDE.md.

**Known consequence, accepted.** `closePanel()` returns focus to `[data-id="${F.panel}"]`. When
the user navigates panel-to-panel to an entry filtered out of the current row set, that
selector matches nothing and focus falls to `#q` via the existing `|| ` branch. That is a sane
landing spot. The alternative — clearing the filter so the row exists — means a click inside a
panel silently rewrites the user's facets, which is the class of thing `syncFacets()` exists to
prevent. Recorded as a decision rather than left as an oversight.

### 7. Scope, against the MAP

`MAP.md` puts "analytics dashboards, charts, or trend lines over skill usage" out of scope.
A workflow section is not that, and the line will read as though it is. Amend it in the same
commit: the exclusion covers **measurements plotted over time or aggregated across entries**;
one entry's own step structure, read from its own file, is not a measurement. Stated in one
sentence so it is not relitigated.

`DESIGN.md` gains the Workflow component as part of the visual contract.

## Order of work

1. This ticket. Its own commit, before code. Repo convention; 010 and 011 both did it.
2. `step_blocks()` and the `step_section_spread()` rewrite. Its own commit. It is a scanner
   correctness fix that stands alone, and bundling it with a new component means one commit
   where a changed count could be either cause. Measured verdict-neutral above; re-verify on
   the real run.
3. `steps` field, `SCHEMA_VERSION` bump, `UI_ENTRY_FIELDS`.
4. The Workflow section, `wirePanel()`, and the `MAP` / `ROADMAP` / `DESIGN` / `CLAUDE`
   updates together, so the record never lags the behavior.

## Verifying

CLAUDE.md's existing list — search keeps focus and caret, facet change updates the count,
Clear resets controls and rows, mode toggle, column sort, panel open and close,
`agent-browser errors` clean — plus:

- Open `design-sprint`. Workflow renders 11 steps in the file's order, with `discovery-sprint`
  under Step 1 and `ux-flow` under Step 2.
- Open `launch-sprint`. `marketing-sprint` appears under Step 6, not in the trailing group.
- Open `feature-sprint`. Its 2 unresolved names render muted and are not clickable.
- Open `weekly`. Depth-1 cycle, smallest case; the `↺` note renders and does not recurse.
- Open `maintenance-sprint`. `feature-sprint` appears under both Step 4.5 and Step 5.
- Click a target, confirm the panel swaps root and the section re-renders; close from the
  navigated-to panel and confirm focus lands somewhere.
- Open a non-orchestrator. No Workflow section, `Calls` and `Called by` unchanged.

Per CLAUDE.md, `agent-browser click` does not land on `all: unset` text buttons. Focus and
press Enter.
