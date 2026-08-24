# 014 — Does Wayfinder create files, and what a skill's example is

Parent: `../MAP.md`
Label: `wayfinder:grilling` (HITL)
Blocked by: 007, 011, 012
Status: closed 2026-08-20, built in part

## Question

`ROADMAP.md` ideas 7, 8 and 9 are all tier **Later**, and idea 8 was already blocked on this
ticket number by the roadmap's own last section: "Does Wayfinder create files. Forced by ideas 6
and 8." This ticket settles all three.

- **Idea 7, feedback capture.** A textarea on a skill: notes on what to fix next time.
- **Idea 8, skill creator and duplicate buttons.** A button that invokes `skill-creator`, and a
  button that forks a skill — particularly an orchestrator being forked for a different workflow.
- **Idea 9, image or GIF output example.** Show what a skill produces.

The three share one question, which is why they are one ticket: each proposes a control that
would make Wayfinder do something rather than report something. Ideas 7 and 9 turn out not to
need that. Idea 8's strong half does, and that is the decision.

## Measurement, 2026-08-20, against the live 426-entry snapshot and the wider `~/.claude` tree

| Signal | Value |
|--------|-------|
| `SKILL.md` files under `~/.claude` | 1252 |
| ...heading a section named Example, Examples or Usage | 194 (15%) |
| Indexed entries matching a loose `usage\b` prefix rule | 44 of 426 |
| Indexed entries carrying an extractable example after the title rule below | 39 of 426 |
| ...truncated at the 18-line cap | 21 |
| Bytes of example text in the payload | 20,972 |
| Page weight before / after | 629 KB / 658 KB |
| Fields on the `usage` object that carry invocation text | 0 |
| Existing clipboard machinery in the page | `toClipboard()`, `legacyCopy()`, `data-copy`, arm-twice |
| Subcommands on `scan.py` | 0 — one flat `argparse`, `--out` and `--prototype` |

Three of those rows decide the ticket:

**The image has no source and the file already has the answer.** Nobody is drawing 426 GIFs, a
single 200 KB data URI is a fifth of a payload `prune()` fought 22% to shrink, and 194 files
already head an Example or Usage section. That is a literal string, so it is fact, and it costs
no LLM pass. Idea 9's own text says as much and then scores itself on the image.

**Usage cannot supply an example either.** The `usage` object is counts, channels and timestamps.
`scan_transcripts()` never keeps the invocation text. This is the same wall idea 5 hit in 012, and
it is worth stating twice so nobody proposes "show a real invocation from the transcripts" a third
time.

**The clipboard is already built.** 011 shipped `toClipboard()` with an `execCommand` fallback for
`file://` origins that refuse the async API. Ideas 7 and 8 both wanted "put text somewhere the
user can paste it", so the honest version of each is new markup over existing machinery, not new
machinery.

## Resolution

### 1. Idea 9 is split. The image is closed; the file's own example ships.

Closed, and not for cost. There is no source. Extract instead.

The rule, in `attach_examples()`:

- ATX headings only, collected fence-aware, because a skill about writing skills quotes
  `## Usage` inside a code block. `headings()` tracks the open fence marker and skips anything
  inside it.
- Depth 2 or deeper. A document whose `#` title is "Examples" is an examples document, not a
  skill with an example section.
- First match wins. Title matches `examples?\b` as a prefix, or `usage` / `usage examples`
  standing alone. `usage\b` as a prefix was measured first and matched 44 entries against the
  tight rule's 39. The five it adds are `Usage Emails`, `Usage Limits`, `Usage Instructions`,
  `Usage modes` and `Usage Patterns`. The first two are policy sections and plainly wrong; the
  other three probably do contain examples. Tightening loses them on purpose, because the panel
  labels this block **Example** in Wayfinder's own words, and a policy section under that label is
  the page fabricating a framing even though the quoted text is real. A skill whose only such
  section is `Usage Patterns` still gets its path handed over, which is what the panel does for
  the other 387.
  `Example: Form submission` on `agent-browser` and `Example interaction` on eleven others are the
  reason the `Example` side stays a prefix match.
- The section ends at the next heading of equal or shallower depth, or at EOF. Blank edges
  trimmed.
- Capped at 18 lines and 1400 characters, whichever comes first, and `example_truncated` records
  that it happened. A 12-line / 900-character cap was measured first and truncated 26 of the 44
  matches; 18 / 1400 truncates 21 of 39 and costs 3.5 KB more. Truncation is common either way,
  which is why the note says "first lines only" and points at the path.

Three fields, `example`, `example_from`, `example_truncated`. `example_from` is the literal
heading text, so the page can name the section it quoted rather than claiming an "example" the
author called something else. Nothing is rewritten, reflowed or summarised: it is `<pre>` with
`white-space: pre`, so a truncated fence renders as the unterminated fence it is.

Absent is stated by the section not being in the panel at all. That is the rule 012's Workflow
section already follows: no heading in the file, no block on the page, no fabricated stand-in.
387 of 426 entries show nothing here, which is correct — the file has no example, and the panel
already hands over the path.

### 2. Idea 7 ships as a clipboard handoff. `data/notes.json` is not built.

A textarea in the panel and a **Copy a revision prompt** button. The prompt carries the skill
name, its path, the note, and an instruction to read the file before changing it.

`localStorage` is not used. Under `file://` it is origin-quirky across browsers and loses data
silently, and a box that forgets without saying so is worse than no box. So the panel says the
box is not saved, in the same note that says Wayfinder never writes to a skill.

`data/notes.json` with a `scan.py note` subcommand is the durable version and the roadmap
recommends it as a promotion. It is not built, for a reason worth writing down: getting text from
a `file://` page into a JSON file means copy and paste either way. The only thing `notes.json`
buys today is that you paste into a CLI instead of into Claude Code, and pasting into Claude Code
is where the revision actually happens. Promote it when a note exists that was wanted and lost.

### 3. Idea 8 ships its fork **prompt**. `scan.py fork` is refused, and the MAP line stands.

Two halves, and they get opposite answers.

**The `/skill-creator` button is dropped, not deferred.** It would copy a nine-character string
that is faster to type than the panel is to open. There is no version of it that earns a control.

**The fork prompt ships.** A **Copy a fork prompt** button, shown only where the entry has a
closure — `delegates_to` or `delegates_to_unresolved` non-empty. The prompt names the original
path, says to leave it untouched, and lists the closure with an instruction to ask per reference
before rewriting it. The two lists are unioned through a `Set`: `delegates_to_unresolved` is not
subtracted from `delegates_to`, so `launch-sprint` named three skills twice before the dedupe.

**`scan.py fork <id> <new-name>` is refused.** `MAP.md` already puts "editing, creating, or
version-bumping skills from inside the tool" out of scope, and the roadmap is right that decision
1 covers editing an existing `SKILL.md` rather than writing a new one — the gap is real. It is
closed the same way it was left, deliberately, and here is the argument the roadmap asked for:

Decision 1 forbids editing a skill because the skill file is the source of truth and Wayfinder is
an index over it. Writing a *new* directory corrupts no source of truth, so it does not violate
decision 1 on its own terms. What it does instead is make the next scan index something Wayfinder
wrote. The tool starts reading its own output, and every number on the page — 426 entries, 167
global, the never-used count — becomes partly a measurement of the tool. That is a worse property
than the inconvenience it removes, and the inconvenience it removes is one paste.

The prompt version has the same closure knowledge, does the same work, and leaves the writing
with the agent that can ask a question mid-way. If someone forks often enough for the paste to
chafe, reopen this with the count.

### 4. Schema and payload

`SCHEMA_VERSION` 2 → 3. Three new entry fields, all in `UI_ENTRY_FIELDS`. `prune()` handles them
without change: `example` and `example_from` are dropped when null, `example_truncated` when
`False`, which is 387 entries carrying none of the three. Payload cost is 29 KB on the page, 21 KB
of it the example text itself.

Nothing new is inferred, so no sidecar field and no prompt change. Everything here is either a
literal string from the file or a string the page composes from fields it already has.

### 5. Listeners

The two buttons bind in `wirePanel()`. That is forced, not chosen: `openPanel()` rebuilds the
panel with `innerHTML` on every open, so anything inside it binds there or not at all.

They cannot use the dialog's `data-copy` attribute. The revision prompt reads the textarea at
click time, so the payload does not exist when the markup is written. Each button gets a `said`
span after it and a click handler that calls `toClipboard()` with a thunk. `wireAsk()` is left
alone: its arm-twice state for `rm -rf` is real behaviour that neither of these buttons wants.

### 6. Scope, against the MAP

Nothing here reverses a MAP decision, and one line deserves a note rather than an amendment.
"Editing, creating, or version-bumping skills from inside the tool" is out of scope and stays out
of scope; §3 above is the argument for keeping it there, now that a ticket has actually made it.
The MAP's 014 entry should say so, because the gap decision 1 left open is now closed on purpose
instead of by omission.

`DESIGN.md` gains the Example block and the Hand off section as part of the visual contract. Both
borrow the Workflow section's heading and provenance-note pattern rather than inventing a third,
which is why `.flow-wrap h3` and `.flow-wrap .note` gained `.hand` selectors instead of being
copied.

## Order of work

1. This ticket. Its own commit, before code. Repo convention; 010, 011 and 012 all did it.
2. `headings()`, `attach_examples()`, the three fields, `SCHEMA_VERSION`, `UI_ENTRY_FIELDS`.
3. The Example block, the Hand off section, `wirePanel()`, and the
   `MAP` / `ROADMAP` / `DESIGN` updates together, so the record never lags the behavior.

## Verifying

CLAUDE.md's existing list — search keeps focus and caret, facet change updates the count, Clear
resets controls and rows, mode toggle, column sort, panel open and close, `agent-browser errors`
clean — plus:

- Open `ab-testing`. Example renders from its `Example` section, no truncation note, no fork
  button (it has no closure).
- Open `deep-research`. Example renders from `Examples` with the "first lines only" note.
- Open `agent-browser`. The section is named `Example: Form submission`, not "Example", because
  `example_from` is the author's heading.
- Confirm no entry shows a section named `Usage Limits` or `Usage Emails`; the title rule excludes
  `usage` used as a prefix.
- Open a plugin skill with no example. No Example block at all, not an empty one.
- Type a note, focus **Copy a revision prompt**, press Enter. The `said` span reads Copied, and
  the prompt contains the note text and the full path.
- Open `launch-sprint`. Both buttons present. The fork prompt names each of its five references
  exactly once.
- Close and reopen the panel. The note box is empty again, which is what the note under it says.

Per CLAUDE.md, `agent-browser click` does not land on `all: unset` text buttons. Focus and press
Enter. Note also that a search term can leave the row outside the selected band: `feature-sprint`
returns no clickable row while the strip sits on Never called.
