# Roadmap: candidate work after 009

Parent: `MAP.md`
Status: draft, no decisions locked
Written: 2026-08-19

Eleven ideas, scored and ordered. Nothing here is a decision. Each entry states what it is, what
it costs, what already exists that it can lean on, and which of the repo's four hard constraints
it collides with.

The constraints, restated because most of the friction below comes from them:

1. Never write to a `SKILL.md`. The tool hands over a path.
2. No build step, no framework, no dependency beyond PyYAML.
3. No ES modules, no external `<script src>` or `<link>` for app code. `file://` blocks them.
4. Generated files never ship.

A fifth, from `PRODUCT.md`: the page never fabricates a number, and absent data reads as unknown.
Several ideas below are ways to put a confident-sounding judgment on a row. Each one has to say
where the judgment came from.

---

## Scoring

Each idea scored 1-5 on three axes. `Value` is how much it moves the product's stated job, which
is recall, not lookup. `Cost` is build effort in this repo, where the honest unit is "how much
`scan.py` and inline JS does it add". `Fit` is how well it survives the constraints without
bending one.

Priority is `Value x Fit / Cost`, rounded to a tier by judgment, not arithmetic.

| # | Idea | Value | Cost | Fit | Tier |
|---|------|-------|------|-----|------|
| 1 | Risk assessment of permissions and data reach | 5 | 3 | 5 | **Now** |
| 2 | Duplicate skill finder | 5 | 2 | 5 | **Now** |
| 3 | One-liner gloss above the full description | 3 | 1 | 4 | **Now** |
| 4 | Orchestration workflow visualization | 4 | 3 | 4 | **Next** |
| 5 | Best inputs and outputs for a skill | 4 | 2 | 3 | **Next** |
| 6 | Copy and share, with orchestration bundling | 4 | 4 | 2 | **Next**, gated |
| 7 | Feedback capture for future refinement | 3 | 2 | 2 | **Later** |
| 8 | Skill creator and duplicate buttons | 3 | 2 | 2 | **Later** |
| 9 | Image or GIF output example | 2 | 3 | 1 | **Later** |
| 10 | Is this skill worth turning into an app | 2 | 2 | 2 | **Probably not** |
| 11 | Video on how to use | 2 | 4 | 1 | **Probably not** |

---

## Tier: Now

### 1. Risk assessment of permissions and data reach

**The idea.** Every row carries a plain statement of what the skill can touch: which tools it is
allowed to call, whether it reaches the network, whether it writes or deletes files, and whether
it handles credentials or personal data. No skill should be a security or data surprise.

**Why it is first.** The library has 426 rows and 257 of them are plugin skills written by other
people. Eli reads a fraction of them. This is the one question in the whole backlog where not
knowing the answer has a cost outside the tool.

**Ground truth, measured 2026-08-19 against the live 426-entry snapshot.** All 426 `SKILL.md`
files read; regex counts, so a floor rather than a ceiling:

| Signal | Entries |
|--------|---------|
| Declares `allowed-tools` in frontmatter | 2 |
| Body contains `curl` or `wget` | 22 |
| Body contains `rm -rf` | 1 |
| Body mentions `API_KEY`, `SECRET`, `TOKEN`, or `credential` | 166 |
| Body contains a `POST`/`PUT`/`DELETE` to an http URL | 2 |

Across the wider `~/.claude` tree, including plugin skills the scanner does not index, the same
regexes hit 19 `allowed-tools`, 61 `curl`/`wget`, 15 `rm -rf`, and 525 secret-word matches.

**What the numbers mean.** Two things, and they point in opposite directions.

Two entries out of 426 declare `allowed-tools`. The permission model this idea assumed exists,
does not. A skill's real capability is whatever the agent running it is allowed to do, and the
skill file says nothing. So the honest form of this feature is not "what permissions does it
request", because almost nothing requests anything. It is **what does the body of this skill
instruct an agent to do**.

The 166 secret-word matches are mostly noise. `TOKEN` matches "token budget" and "tokenizer";
this is a skill library about LLM tooling. A flag firing on 39% of the library is not a signal, it
is a decoration. That count is the argument for the two-tier pattern, not against the feature.

**Shape it should take.** The same two-tier architecture as tickets 003 and 009: cheap mechanical
checks that are precise enough to state as fact, plus a batched LLM adjudication for the rest,
with the verdict written to the sidecar and carrying its provenance.

Tier one, stated as fact, each one a literal string in the file:

- Declares `allowed-tools`, and what it lists.
- Contains a destructive shell pattern: `rm -rf`, `git push --force`, `DROP TABLE`, `> ` onto a
  tracked path.
- Contains an outbound network call: `curl`, `wget`, a `fetch(` to a non-localhost URL, an
  http(s) URL passed to a write verb.
- Bundles executable resources: a `scripts/` directory with `.py` or `.sh` in it. 95 skill
  directories under `~/.claude` have one.
- Names an MCP server or connector, which means a live external account.
- Reads outside the project: `~/.ssh`, `~/.aws`, `.env`, keychain, browser profile paths.

Tier two, adjudicated and labelled as inferred, one batched pass over only the entries tier one
flagged:

- Does this skill send anything off the machine, and what.
- Does it write or delete anything the user did not name.
- Would a reasonable person be surprised by either.

Output is a three-state field per entry, not a score: `no reach`, `reaches out` with a one-line
reason, and `needs a read` when the adjudicator was not confident. Never a number. A "risk: 7/10"
on a row is exactly the fabricated number `PRODUCT.md` forbids.

**Cost.** A new scanner pass, a sidecar field, a facet, and a block in the entry panel. It reuses
the 003/009 machinery, so most of the cost is writing the checks and the prompt.

**Open question worth a ticket.** The 257 plugin entries are the population most in need of this
and the population Eli cannot fix. Does a flag on a plugin skill mean anything actionable, or does
it just make the library feel unsafe? Proposal: yes, index them, because the action is "stop using
it", which is available.

### 2. Duplicate skill finder

**The idea.** Photos-style near-duplicate detection. Group skills that overlap, show them side by
side, recommend which to keep.

**Why it is high value and cheap.** It serves recall directly, which is the stated job. It is a
pure read over data already in the snapshot, so it violates nothing. And the library visibly has
duplicates already: `vercel:*` and `vercel-plugin:*` are near-identical twins across dozens of
entries, `agent-browser` exists as both a global skill and a plugin skill, and `figma` and
`plugin_figma_figma` shadow each other.

**Signals, all already on disk or one line away:**

- Identical or near-identical `id` after stripping a plugin prefix. This alone catches the
  `vercel` / `vercel-plugin` family.
- Byte-identical or high-similarity `SKILL.md` body. `difflib.SequenceMatcher` is standard
  library; no dependency.
- Same `upstream_url`.
- Same domain and kind, plus a high description similarity.
- One is a symlink or repo twin of the other. `is_symlink` and `repo_differs` already exist.

**The recommendation, and where it must stop.** Rank the members of a group by evidence the tool
actually has: usage count and recency, `body_lines`, `has_resources`, `parse_status`, health
flags, and whether it is Eli's or a plugin's. Say which one the evidence favors and why, in one
line. Then hand over both paths. It never deletes, never edits, never merges. Constraint 1 is not
negotiable for this feature and the temptation to add a "merge" button will be real.

**Cost.** A grouping function in `scan.py`, a `duplicate_group` field, and a view. The pairwise
comparison at 426 entries is trivial; blocking on `(domain, kind)` keeps it that way if the
library grows.

### 3. One-liner gloss above the full description

**The idea.** In the slide-out, a short line above the paragraph. Scanning 426 rows means reading
descriptions written to trigger a model, not to inform a person. Several run 80 words.

**Two ways to get it, and they are not equal:**

- **Free and honest:** first sentence of the description, truncated. Zero new machinery, but many
  descriptions start with "Use when the user..." which is trigger text, not a gloss.
- **Better and inferred:** a `gloss` field in the sidecar from the same LLM pass that already
  produces domain and kind. Marginal cost on a pass that already runs. It must be labelled
  inferred, like every other sidecar field, per principle 5.

Recommendation: the sidecar field, with the first-sentence fallback when the sidecar is missing,
because the page has to be correct on a machine that never ran the LLM pass.

**Cost.** One prompt change, one field, one line of markup. The cheapest thing in this document.

---

## Tier: Next

### 4. Orchestration workflow visualization

**The idea.** Draw the graph. `delegates_to`, `delegates_to_unresolved`, and `reached_via` already
exist on every entry, and the entry panel already lists them as flat text. A picture of a
multi-step orchestrator is the one thing text does badly.

**What the data supports.** Ticket 003 settled the extraction and 006's Q12 resolution dropped the
candidate count from 71 to 25. Ten entries carry an `orchestration_verdict`. So this is a picture
of a small graph, not a hairball, which is the case where node-link diagrams actually work.

**The constraint fight.** No dependency, no build step, no external script. That rules out every
graph library. It does not rule out a diagram: for a directed acyclic graph of under ~30 nodes,
inline SVG with a hand-rolled layered layout is maybe 80 lines of JS. Layer by longest path from
the roots, space within a layer, draw edges as cubic beziers. If a graph turns out to be cyclic,
say so and fall back to the list.

**The tension to note honestly.** `MAP.md` puts "analytics dashboards, charts, or trend lines over
skill usage" out of scope. A call graph is not a usage trend line, so this does not reverse that
decision. If it ships, the MAP should say why the distinction holds.

**Scope discipline.** One orchestrator's graph, opened from its panel. Not a whole-library map.
The library-wide version is a hairball at 426 nodes and would be a demo, not a tool.

### 5. Best inputs and outputs for a skill

**The idea.** On the panel: what to give this skill, what you get back.

**Where it comes from.** Nowhere reliable, which is the problem. Some skills document it, most do
not. The honest options are to extract it when the file states it, and adjudicate otherwise. This
is a good sidecar field and a bad fact.

**One better source than the file.** Usage evidence. The snapshot already knows which skills call
which, so "typically called after X, typically hands off to Y" is derivable and true. That is a
narrower claim than "best inputs" but the tool can actually make it.

Recommendation: ship the derived-from-usage version first, since it is free and factual. Treat the
LLM-written "best inputs" as a separate, later, clearly-inferred field.

### 6. Copy and share, with orchestration bundling

**The idea.** A copy-and-share action. For an orchestrator, bundle it with everything it calls, so
a colleague can import the whole workflow rather than a broken root node. Land it somewhere a
person can drop into their own `~/.claude/skills`, or upload to the desktop or web app.

**This is ticket 007 and it is already specified.** 007 is closed with a resolution and
deliberately not built. Re-read it before touching this. Its rules, which this idea must inherit:

- **Allowlist only, fail closed.** Nothing is published by omission. Today `publishable` is
  `false` on all 426 entries, which is the correct starting state.
- The allowlist lives in `data/overrides.json`, keyed on `id`. Not the sidecar, which the LLM pass
  regenerates, and not the skill's frontmatter, which the tool never writes.
- Publishing is a **second command emitting a filtered artifact**, not the same snapshot with the
  UI hiding rows. A hidden row is still in the file.

**What this idea adds to 007 that 007 does not cover, and needs its own ticket:**

- **Transitive allowlisting.** Bundling an orchestrator means shipping its dependencies. If the
  root is allowlisted and a leaf is not, the bundle is broken or the leak is silent. Proposal:
  refuse to bundle, name the missing leaves, and make the user allowlist each one. Fail closed
  applies to the closure, not just the root.
- **Plugin skills are not Eli's to share.** 007 question 5. A bundle that pulls in a plugin skill
  is redistributing someone else's work. Proposal: reference by name and install instructions,
  never by copy.
- **Format.** A `.zip` of skill directories is the shape both the desktop app and a manual drop
  into `~/.claude/skills` accept. Emitted by `scan.py`, not by the page: `file://` cannot write a
  file, and this is exactly the kind of thing that should not be one click away.

**Why it is Next and gated rather than Now.** Its blast radius is the largest in this document.
Everything else is a read; this one sends data off the machine. 007's own measurement found 33 of
169 personal skills flagged by a deliberately crude personal-content regex, and called that a
floor.

---

## Tier: Later

### 7. Feedback capture for future refinement

**The idea.** A textarea on a skill: notes on what to fix next time.

**Why it is awkward here, not why it is a bad idea.** The page runs from `file://` with no server.
It cannot write a file, and constraint 1 says it must not write to the `SKILL.md` anyway.
`localStorage` under `file://` is origin-quirky across browsers and silently loses data, which is
worse than not offering the box.

**The version that fits.** The textarea produces text, and a Copy button puts it on the clipboard
as a ready-to-paste prompt: the skill's name, its path, the note, and an instruction to open and
revise it. The tool ends at a handoff, which is principle 3, and the note goes where the work
happens rather than into a store the page cannot keep.

**The version that would be better and costs more.** Notes land in `data/notes.json`, hand-edited
or written by a small `scan.py note` subcommand, and the page renders them as another tracked
sidecar like `overrides.json`. That is durable, greppable, and version-controlled. It needs a way
to get text from the page into the file, which off `file://` means copy and paste anyway.

Recommendation: clipboard handoff first. Promote to `data/notes.json` if the notes accumulate.

### 8. Skill creator and duplicate buttons

**The idea.** A button that invokes `skill-creator`, and a button that duplicates a skill,
particularly an orchestrator being forked for a different workflow.

**What the page can actually do.** Not invoke anything. `file://` has no channel to the harness.
The realistic version is a Copy button that puts `/skill-creator` or a filled-in duplicate
instruction on the clipboard, which the user pastes into Claude Code. That is a real convenience
and it is honest about what it is. Labelling it "Create skill" when it copies a string is not.

**The duplicate case is the stronger half.** Forking an orchestrator is a genuine workflow, and
the tool already knows the closure to copy: `delegates_to` gives the leaves. A `scan.py fork
<id> <new-name>` subcommand could write a new directory under `~/.claude/skills`, with the
prefixed references rewritten.

**But note what that is.** It writes to `~/.claude`. Constraint 1 forbids writing to an existing
`SKILL.md`; writing a brand new one is not literally that, but it makes Wayfinder a tool that
creates things. That is a genuine change in what the product is and it belongs in a ticket that
argues it, not in a button someone adds on a Tuesday.

Cross-reference: this shares its whole closure-walking mechanism with idea 6. If both ship, they
share code.

### 9. Image or GIF output example

**The idea.** Show what a skill produces.

**The problems, in order.** There is no source for the images; someone has to make 426 of them, or
some subset, by hand. Constraint 3 forbids external asset references for app code, and while an
`<img src="assets/...">` is not app code, it does break "distribution is copying two files".
Inlining as data URIs is the alternative, and a single 200KB GIF is a fifth of the current
payload; the `prune()` work exists because 22% of page weight mattered.

**The version worth considering.** Not images. A short text example of a real invocation and its
real result, for the handful of skills where it is unambiguous. Cheap, inline, and it does the same
job the image was meant to do.

If a visual is genuinely needed, the honest home is the skill's own directory, and the page links
to the path like it does everything else.

---

## Tier: Probably not

### 10. Is this skill worth turning into an app

**Why it is scored low.** It is a business judgment with nothing on disk behind it. The tool would
be asking an LLM to speculate, printing the speculation next to measured usage counts, and
inheriting the credibility of the numbers around it. `PRODUCT.md` says the page never fabricates
and that evidence beats inference. This is inference wearing evidence's clothes.

**What is real underneath it.** The question people actually mean is "which of my skills are
substantial and reused enough to matter". The tool already answers that with usage count, recency,
`body_lines`, `has_resources`, and orchestration degree. A "most substantial, most used" view is
the same insight built from facts.

**If it ships anyway.** Keep it out of the row and out of the panel. It belongs in the insights
panel as an explicitly speculative section, or in a one-off report that is not the product.

### 11. Video on how to use

**Why it is scored low.** A video of a tool that changes weekly rots faster than it is made. The
constraints make hosting it inside the page impossible at any reasonable weight, so it lives
elsewhere, which means the page links out to something that will drift out of date.

**What the page already does instead.** It explains its own vocabulary on purpose, for the
teammate audience in `PRODUCT.md`. That is the durable version of onboarding for a single-page tool
and it is already the design.

**The cheap 80%.** A `README` section with a labelled screenshot and five sentences. If that turns
out not to be enough, the video argument gets stronger and can be revisited with evidence.

---

## Suggested order

1. **Duplicate finder** (idea 2). Highest value per unit of cost, pure read, no constraint fights,
   and the library visibly has duplicates today.
2. **One-liner gloss** (idea 3). Nearly free, rides an existing LLM pass.
3. **Risk assessment** (idea 1). Highest value overall; needs a ticket first because the
   measurement above shows the obvious framing, "what permissions does it request", is the wrong
   one.
4. **Usage-derived inputs and outputs** (idea 5, the factual half). Free, derived from the graph
   that already exists.
5. **Orchestration visualization** (idea 4). Do it after 5, since both work the same graph.
6. **Publish and bundle** (idea 6). Only when someone actually wants to publish, and only through
   007's rules.

Everything else waits for evidence that it is wanted.

## Tickets this implies

Following the repo's own convention, three of these need a decision ticket before code:

- **010 — What "risk" means when nothing declares permissions.** Two entries of 426 declare
  `allowed-tools`. Decide whether the unit is declared permission or instructed behavior, what is
  fact versus adjudged, and whether plugin entries are flagged.
- **011 — Duplicate grouping and the keep recommendation.** Which signals define a group, how the
  recommendation is ranked, and the explicit refusal to merge or delete.
- **012 — Does Wayfinder create files.** Forced by ideas 6 and 8. Bundling writes a `.zip`,
  forking writes a new skill directory. Decision 1 covers editing existing skills, not creating
  new ones, and that gap should be closed deliberately rather than by a button.
