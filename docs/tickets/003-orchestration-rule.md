# 003 — How to detect an orchestration skill

Parent: `../MAP.md`
Label: `wayfinder:research` (AFK)
Blocked by: none
Status: closed 2026-08-18 (see Resolution)

## Question

What reliably marks a skill as an orchestrator (a skill that sequences other skills), and can it
be detected without a per-skill LLM pass?

Known examples to test any rule against: `feature-sprint`, `design-sprint`, `pm-orchestrator`,
`growth-sprint`, `launch-sprint`, `marketing-sprint`, `maintenance-sprint`, `discovery-sprint`,
`wayfinder`, `council`.
Known non-examples that may false-positive because they mention other skills in prose:
`design-accelerator`, `zoom-out`, `using-superpowers`.

Research must establish:

1. What signals actually exist in the bodies. Candidates: a `Skill(` call, a `/skill-name`
   reference, an explicit "invoke", "sequences", "orchestrates" phrase, a numbered step list
   naming other skills.
2. Precision and recall of the best cheap rule, measured against a hand-labelled sample of at
   least 30 skills spanning both populations.
3. Whether it is a boolean or a degree (orchestrates 1 skill vs sequences 6).
4. Whether the inverse is worth capturing too: which skills are *called by* an orchestrator.
   That answers "this skill is never reached on its own" and may be more useful than the badge.
5. Whether this belongs in the same sidecar as category, given both are inferred.

Report the rule, its measured accuracy, and the false positives it keeps.

## Resolution

Status: closed. Measured on disk 2026-08-18 against 167 personal `SKILL.md` files (172 directories, 5 have
no `SKILL.md`) and 1190 plugin files, 1357 total.

### Headline

A cheap rule exists and is worth shipping, but not as a standalone badge. The best rule scores
precision 0.71 and recall 0.86 on a 66-skill hand-labelled sample. That is good enough to generate
candidates and good enough to power a filter facet when the UI also shows the evidence, and not good
enough to stamp an unreviewed "orchestrator" badge on a skill. The recommendation is therefore a
two-part field: the scanner computes the reference graph mechanically for all 1357 skills, and a
single batched LLM call adjudicates the 46 candidates the rule surfaces. That is one LLM call for the
whole library, not 1362, so the "no per-skill LLM pass" constraint is honoured.

The more valuable finding is question 4. The inverse relation is stronger, cheaper, and better
validated than the badge, and it should probably lead the feature.

### Two corrections to the ticket's ground truth

Reading the bodies invalidated two of the ten named orchestrators, so any rule scored against the
original list would have been scored against a wrong answer key.

- `marketing-sprint` calls itself a "build-in-public orchestrator" in its own first line and
  delegates to zero other skills. It sequences its own internal modes. No rule based on skill
  references can or should flag it.
- `council` orchestrates five subagent personas, not skills. It references no skill at all.

Both are labelled negative below. The lesson for the spec: "orchestrator" in Eli's prose sometimes
means "multi-step" or "spawns subagents", which is a different property from "sequences other
skills". If the UI badge is going to say "orchestration skill", it needs to pick one meaning and the
skill descriptions will not agree with it.

### What signals actually exist (question 1)

Frequency across all 1357 files:

| Signal | Files | Notes |
|---|---|---|
| `Skill(` tool-call syntax | 9 | all plugin, zero personal. Unusable. |
| `skill://` URI | 0 | does not occur |
| `/slash-name` reference to a known skill or command | dominant form in personal skills | |
| `skills/<name>/SKILL.md` path reference | 47 | 1 personal, 46 plugin. The `pm-skills` marketplace convention. |
| "the `<name>` skill" prose form | scattered | the form `pm-orchestrator` uses throughout |
| Any distinct reference to another known skill or command | 318 | |
| Same, excluding "References / Related Skills / Dependencies" footers | 311 | |
| Same, in imperative or step position | 206 | |
| Two or more such references | 46 | |
| Two or more in distinct `Step N` / `Phase N` sections | 38 | |
| `orchestrat` / `sequenc` / `sub-skill` in frontmatter | 71 | |
| Same anywhere in body | 206 | |

Two mechanical traps have to be handled or the rule collapses:

1. **The reference vocabulary must include `~/.claude/commands/*.md`, not just skill directories.**
   `feature-sprint` sequences `/prime`, `/plan-feature`, `/tdd`, `/zoom-out`, `/execute`. Three of
   those five are commands, not skills. A skills-only vocabulary scores `feature-sprint`, the
   flagship orchestrator, at one reference. This settles part of the MAP's open question about
   whether `~/.claude/commands` belongs in the library: whether or not commands get their own rows,
   they must be in the name table, or the orchestration graph is wrong.
2. **The `pm-skills` marketplace stamps a "Related Skills" and "Dependencies:" footer on every leaf
   skill.** Raw reference counting flags roughly thirty leaf component skills (`proto-persona`,
   `press-release`, `problem-statement`, `jobs-to-be-done`, `positioning-statement` and siblings) at
   four references each. Stripping `## References`, `### Related Skills`, `**Dependencies:**` and
   `**Used by:**` blocks drops all of them to zero and is the single largest precision gain
   available.

A third trap is smaller but real: bash snippets produce phantom matches. `benchmark-agents` scored
`ai-elements` and `workflow` from `find` globs inside fenced code. Excluding fenced code blocks would
remove it.

### The recommended rule

Compute, per skill:

- `refs` = distinct names from the union of `/slash`, `Skill(`, `` `name` skill ``, and
  `skills/name/SKILL.md` forms, matched against a vocabulary of all skill directory names plus all
  command basenames, minus self-references. Generic English words that are also skill names
  (`review`, `research`, `plan`, `launch`, `design`, `image`, `video`) count only via the
  unambiguous `/slash` or `Skill(` forms.
- Drop references occurring only inside reference-footer sections, and only inside terminal
  "Next Steps" / "handoff menu" / "what would you like to do next" blocks.
- Keep references that sit on a line carrying a call verb (`run`, `invoke`, `use`, `call`,
  `delegate`, `hand off to`, `route to`, `depends on`, `sequences`) or on a numbered-step or heading
  line. Call the surviving count `degree`.

**Rule: `degree >= 2` AND (`orchestrat|sequenc|sub-skill` appears in frontmatter OR the surviving
references are spread across two or more distinct `Step N` / `Phase N` sections).**

Measured on the 66-skill hand-labelled sample (14 positive, 52 negative):

**Precision 0.71, recall 0.86, F1 0.77. 12 true positives, 5 false positives, 2 false negatives.
Flags 17 of 1357 skills corpus-wide.**

Alternatives measured on the same labels, for the record:

| Rule | P | R | F1 | Corpus flagged |
|---|---|---|---|---|
| any reference anywhere >= 1 | 0.27 | 1.00 | 0.43 | 318 |
| any reference anywhere >= 2 | 0.39 | 1.00 | 0.56 | 103 |
| body reference (footers stripped) >= 2 | 0.40 | 1.00 | 0.57 | 91 |
| imperative reference >= 2 | 0.50 | 1.00 | 0.67 | 47 |
| imperative reference >= 3 | 0.65 | 0.79 | 0.71 | 20 |
| strict reference >= 2 | 0.52 | 1.00 | 0.68 | 46 |
| strict reference >= 3 | 0.69 | 0.79 | 0.73 | 19 |
| frontmatter word alone | 0.67 | 0.71 | 0.69 | 71 |
| body word alone | 0.36 | 0.64 | 0.46 | 206 |
| strict >= 2 AND frontmatter word | 0.83 | 0.71 | 0.77 | 12 |
| **strict >= 2 AND (frontmatter word OR >= 2 step sections)** | **0.71** | **0.86** | **0.77** | **17** |

Note the shape of the tradeoff. `strict >= 2` alone has perfect recall on this sample and flags 46
skills. Everything above that threshold is a precision play. Since the whole population of candidates
is 46 files, the pragmatic answer is to use `strict >= 2` as the recall-safe candidate generator and
spend one batched LLM call adjudicating those 46 rather than tuning the rule further. The tighter
rule is what to ship if no LLM call is acceptable at all.

The word signals alone are not usable. "Orchestrat" or "sequenc" appears somewhere in the body of 206
skills, and using that as the rule scores F1 0.46. Frontmatter-only is better at 0.69 but misses
`wayfinder`, `discovery-sprint`, `implement`, and `style-tiles`, none of which advertise the word,
and it flags `wireframe-ready`, which is a leaf skill whose description happens to say the word.

### Residual false positives it keeps

All five are the same failure mode with two variants. The rule cannot distinguish "I invoke this
skill as my next step" from "I borrow this skill's output format" or "here is what you might do next".

- `client-intake` (personal). Ends with "Next: run `/discovery-sprint` after the kickoff call" and
  hands its outline to `/pptx`. Two terminal handoffs, not a sequence. Frontmatter says "sequences",
  which is what trips the rule.
- `lean-ux-canvas` (plugin). Its references are all inside "Agent suggests starting with X" branch
  options and a related-skills gallery that does not match the footer patterns because it is written
  as a markdown link list.
- `recommendation-canvas` (plugin). Uses the epic-hypothesis, positioning-statement, and
  problem-statement *formats*. Borrows structure, invokes nothing.
- `user-story` and `user-story-splitting` (plugin). Mutually reference each other plus
  `proto-persona` as prerequisites and as split-check advice.

The two false negatives are both legitimately hard:

- `implement` (personal) is 302 characters: "Use `/tdd` where possible" then "Once done, use
  `/code-review`". A genuine two-step sequence with no step headings and no frontmatter word. Any
  structural rule misses it. It is the argument for a `degree >= 2` recall-safe tier.
- `wayfinder` (personal) delegates to `/grilling`, `/prototype`, and `/research` inside a numbered
  list rather than `Step N` headings, and its frontmatter does not say the word.

One case sits outside the binary and is worth a spec decision rather than a rule tweak. `ask-matt` is
a router: eighteen skill references, an explicit documented flow from `/grill-with-docs` through
`/to-spec`, `/to-tickets`, `/implement`, `/tdd`, `/code-review`, and `disable-model-invocation: true`
so it never runs anything. It has the highest orchestration *content* of any personal skill and
executes nothing. I labelled it negative. Every high-recall rule flags it. If the library grows a
third value, `router`, `ask-matt` is its only member today and the label stops being wrong.

### Question 3: boolean or degree

Capture degree, render boolean. The degree distribution is informative and free once the graph is
built: `product-strategy-session` 16, `discovery-process` and `prd-development` 10, `design-sprint`
8, then a cluster of four at four references, and a tail at two. Degree separates "this is the spine
of a whole workflow" from "this hands off twice", which is exactly the distinction Eli would use to
decide what is worth sharing with the team. But a facet the user filters on should be a checkbox, not
a slider, so the UI filter stays boolean and the degree shows on the row as the count plus the
`delegates_to` list.

Shipping the `delegates_to` list is not optional in this design. It is what makes precision 0.71
acceptable: the user sees "flagged because it references `epic-hypothesis`, `positioning-statement`,
`problem-statement`" and dismisses a false positive in one glance. A bare badge at 0.71 precision
teaches distrust of the whole facet.

### Question 4: the inverse is the better field

Yes, capture it, and consider leading with it. The reverse index is built for free from the same
edges and is better validated than the badge.

From the 17 flagged orchestrators, 46 distinct skills are named as callees, 22 of them personal. Of
those, 30 are called by an orchestrator and call nobody themselves. That is the "never reached on its
own" set. Two independent checks say it is right:

1. It exactly recovers the set `design-sprint` names in its own frontmatter as the skills not to run
   ad hoc. `design-sprint` says "Sequences /ux-flow, /data-modeling, /wireframe-ready, and
   /design-accelerator, do not run those orphan skills ad hoc when this orchestrator applies." The
   reverse index independently derives all four, plus `to-issues`, `grill-me`, `feature-sprint`, and
   `discovery-sprint`. Four out of four on the one case where a human wrote the answer down.
2. 27 of the 30 have zero recorded invocations across the 381 transcript files (178 Skill calls, 46
   distinct skills, window opens 2026-07-20). The three exceptions are `prime` (18 calls), `execute`
   (3), and `to-issues` (1). `prime` and `execute` are commands, and heavily used, which is a
   reminder that commands behave differently from skills and that the MAP's caveat holds: zero is not
   the same as never inside a four-week window.

Why this beats the badge. Precision on an inverse edge is much more forgiving, because a single line
of text is the whole claim and the UI can quote it. And it answers a question Eli actually has. The
badge answers "which of my skills are big"; the inverse answers "which of my 172 skills am I never
going to reach unless I remember the wrapper", which is the forgotten-skills problem the map opens
with. Concretely, `pm-idea-intake`, `pm-effort-time-estimator`, and `pm-roadmap-planner` are
unreachable except through `pm-orchestrator`, and `ux-flow`, `data-modeling`, `wireframe-ready`, and
`design-accelerator` except through `design-sprint`. That is a real finding about the shape of the
library, and it also flags a maintenance risk: a leaf skill that only an orchestrator reaches is a
skill whose description never has to trigger correctly, so it will quietly rot.

Suggested field name `reached_via`, holding the list of orchestrators that name it, empty for
standalone skills.

### Question 5: sidecar placement

Split by cost of recomputation, not by whether the value is inferred.

Put the mechanical fields in `skills.json`, written by the scan script: `delegates_to`,
`reached_via`, `orchestration_degree`, and the rule's boolean verdict. The scanner already opens and
parses every body, the whole computation is a few hundred milliseconds over 1357 files, and it must
be recomputed on every scan because an edge changes the instant either endpoint is edited. Putting a
derived graph in a hand-maintained sidecar guarantees it goes stale, and adding a second file for
something the scanner computes for free is the wrong rung on the ponytail ladder.

Put only the adjudication in the sidecar next to `category`: an override map keyed by skill name with
values `orchestrator`, `router`, `leaf`, plus a short reason string. That is the part a human or an
LLM decided, the part that costs money to regenerate, and the part that should survive a rescan.
Category and this override share the same lifecycle, the same re-run trigger, and the same "one LLM
pass, re-runnable when skills are added" decision already locked as MAP decision 4, so they belong in
one file. The UI reads the override when present and falls back to the rule's verdict.

This also means the LLM pass has a much smaller job than the category pass. Category needs an opinion
on all 1362 skills. Orchestration needs an opinion on the 46 the rule surfaces, which fits in a
single batched call, and the rule's `delegates_to` list can be handed to the model as evidence rather
than making it re-read the bodies.

### The hand-labelled sample

66 skills, 14 positive. Labelling rule applied: a skill is an orchestrator if its own documented
procedure hands control to two or more other named skills as steps of its flow. A single terminal
handoff is a chain link, not a sequence. Borrowing another skill's output format is not delegation.
Spawning subagents is not delegating to skills.

Columns: label, source, name, `degree` (strict count), step-section spread, frontmatter word.

| L | Src | Skill | deg | steps | fm |
|---|---|---|---|---|---|
| 1 | plug | product-strategy-session | 16 | 6 | 1 |
| 1 | plug | discovery-process | 10 | 6 | 1 |
| 1 | plug | prd-development | 10 | 6 | 1 |
| 1 | pers | design-sprint | 8 | 7 | 1 |
| 1 | pers | feature-sprint | 4 | 5 | 1 |
| 1 | pers | launch-sprint | 4 | 4 | 1 |
| 1 | pers | maintenance-sprint | 4 | 3 | 1 |
| 1 | pers | pm-orchestrator | 4 | 4 | 1 |
| 1 | pers | discovery-sprint | 3 | 4 | 0 |
| 1 | plug | roadmap-planning | 3 | 4 | 1 |
| 1 | pers | wayfinder | 3 | 0 | 0 |
| 1 | pers | growth-sprint | 2 | 1 | 1 |
| 1 | pers | style-tiles | 2 | 2 | 0 |
| 1 | pers | implement | 2 | 0 | 0 |
| 0 | pers | ask-matt | 18 | 0 | 0 |
| 0 | plug | lean-ux-canvas | 6 | 2 | 0 |
| 0 | plug | derisk-measurement-advisor | 3 | 0 | 0 |
| 0 | plug | problem-framing-canvas | 3 | 1 | 0 |
| 0 | plug | recommendation-canvas | 3 | 5 | 0 |
| 0 | pers | client-intake | 2 | 2 | 1 |
| 0 | pers | improve-codebase-architecture | 2 | 0 | 0 |
| 0 | pers | week-wrap | 2 | 1 | 0 |
| 0 | plug | analyzing-expensive-users | 2 | 0 | 0 |
| 0 | plug | consuming-endpoints-from-client-code | 2 | 0 | 0 |
| 0 | plug | exploring-scouts | 2 | 0 | 0 |
| 0 | plug | user-story | 2 | 3 | 0 |
| 0 | plug | user-story-splitting | 2 | 3 | 1 |
| 0 | plug | company-intel | 0 | 0 | 0 |
| 0 | pers | diagnosing-bugs | 1 | 1 | 0 |
| 0 | pers | grill-me | 1 | 0 | 0 |
| 0 | pers | marketing-council | 1 | 0 | 0 |
| 0 | pers | marketing-plan | 1 | 0 | 0 |
| 0 | pers | pm-prioritizer | 1 | 0 | 1 |
| 0 | pers | remotion-app-video | 1 | 1 | 0 |
| 0 | pers | tdd | 1 | 0 | 0 |
| 0 | pers | triage | 1 | 0 | 0 |
| 0 | pers | video | 1 | 0 | 0 |
| 0 | plug | benchmark-agents | 1 | 0 | 1 |
| 0 | plug | brainstorming | 1 | 0 | 0 |
| 0 | plug | epic-hypothesis | 1 | 3 | 0 |
| 0 | plug | executing-plans | 1 | 1 | 0 |
| 0 | plug | systematic-debugging | 1 | 1 | 0 |
| 0 | plug | user-story-mapping-workshop | 1 | 1 | 0 |
| 0 | plug | using-superpowers | 1 | 0 | 0 |
| 0 | plug | writing-plans | 1 | 0 | 0 |
| 0 | pers | council | 0 | 0 | 0 |
| 0 | pers | marketing-sprint | 0 | 0 | 0 |
| 0 | pers | design-accelerator | 0 | 0 | 0 |
| 0 | pers | zoom-out | 0 | 0 | 0 |
| 0 | pers | daily-reflection | 0 | 0 | 0 |
| 0 | pers | brand-guidelines | 0 | 0 | 0 |
| 0 | pers | copywriting | 0 | 0 | 0 |
| 0 | pers | grilling | 0 | 0 | 0 |
| 0 | pers | humanizer | 0 | 0 | 0 |
| 0 | pers | prototype | 0 | 0 | 0 |
| 0 | pers | to-issues | 0 | 0 | 0 |
| 0 | pers | ux-flow | 0 | 0 | 0 |
| 0 | pers | wireframe-ready | 0 | 0 | 1 |
| 0 | pers | xlsx | 0 | 0 | 0 |
| 0 | plug | jobs-to-be-done | 0 | 0 | 0 |
| 0 | plug | positioning-statement | 0 | 2 | 0 |
| 0 | plug | press-release | 0 | 2 | 0 |
| 0 | plug | problem-statement | 0 | 2 | 0 |
| 0 | plug | proto-persona | 0 | 3 | 0 |
| 0 | plug | skill-creator | 0 | 0 | 0 |
| 0 | plug | subagent-driven-development | 0 | 0 | 0 |

`company-intel`, `press-release`, `problem-statement`, `proto-persona`, `positioning-statement`, and
`jobs-to-be-done` are the footer-boilerplate cases: they score 3 to 4 references before stripping and
0 after. They are the proof that the footer-stripping step is load-bearing, not cosmetic.

### Caveats on these numbers

- The sample is deliberately enriched with hard cases. Most of the 52 negatives were selected because
  they carried signal. Precision measured here is therefore pessimistic against the full corpus, and
  it is the honest number for the ambiguous zone, which is the only zone where the badge can be
  wrong.
- Plugin skills are duplicated across marketplace copies. `using-superpowers` and
  `systematic-debugging` appear 3 times, `analyzing-expensive-users` and `exploring-scouts` 5 times
  each, `skill-creator` 4. Deduplication belongs to ticket 004, but note that undeduplicated counts
  will inflate any corpus-wide orchestration total.
- Fenced code blocks were not excluded in this measurement. Doing so removes the `benchmark-agents`
  phantom matches and is a free precision improvement.
- Orchestration edges pointing at plugin skills cross the source boundary. `style-tiles` delegates to
  `figma-use`, which is a plugin skill. The Source facet defaults to Eli's 172, so a graph view
  filtered to personal skills will show dangling edges unless the UI resolves callees outside the
  filter.

### What to hand to the spec

1. Scan script computes `delegates_to`, `reached_via`, and `orchestration_degree` into `skills.json`,
   using a name vocabulary of skill directories plus `~/.claude/commands` plus plugin commands, with
   footer sections, terminal next-step blocks, and fenced code excluded.
2. Boolean verdict `degree >= 2 AND (frontmatter word OR two-plus step sections)` written alongside,
   as the pre-adjudication default.
3. Sidecar gains an `orchestration` override map next to `category`, values `orchestrator` / `router`
   / `leaf`, populated by one batched LLM call over the 46 skills with `degree >= 2`.
4. UI: boolean facet, degree and `delegates_to` on the row as evidence, and a "never reached on its
   own" filter driven by `reached_via`. That last one is the field most likely to change what Eli
   does.
