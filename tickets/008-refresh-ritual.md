# 008 — How the snapshot stays current

Parent: `../MAP.md`
Label: `wayfinder:grilling` (HITL)
Blocked by: 005
Status: CLOSED 2026-08-18

## Question

Snapshot architecture buys publishability at the cost of staleness. Decide how it gets refreshed.

Must decide:

1. Trigger: manual command, a slash command, a `SessionEnd` hook, a cron, or on-open by the app.
2. Whether the cheap filesystem/usage scan and the expensive LLM category pass refresh on
   different cadences. They almost certainly should.
3. How a newly added skill surfaces before the LLM pass has categorized it.
4. Whether the UI shows snapshot age, and whether it warns past some threshold.
5. Whether refresh is in scope for the first build at all, or whether "re-run the script" is
   acceptable until it annoys him.

## Resolution

Resolved 2026-08-18. All five questions answered. The short version: refresh is manual, the two
passes run on different triggers, and the first build ships honesty about staleness rather than
automation of it.

### 1. Trigger: manual. `python3 wayfinder/scan.py`, run by hand.

Rejected, with reasons:

- **`SessionEnd` hook.** Adds a 1.34s cost and a new failure surface to every session, in
  exchange for freshness in a tool that gets opened perhaps weekly. Wrong trade by an order of
  magnitude, and a scanner crash inside a hook degrades unrelated work.
- **Cron.** A laptop that sleeps makes cron a lottery, and a schedule that silently stops is
  worse than no schedule, because the age banner is then the only thing that would have caught it.
- **On-open by the app.** Structurally impossible and worth recording as such: the app is a
  static HTML file opened with `open`, with no server and no ability to run Python. This is a
  direct consequence of 006's stack decision, not an oversight.

A `/wayfinder-refresh` slash command is a fine convenience later. It is a wrapper around the same
manual run, not a different architecture, so it does not need deciding here.

### 2. Two cadences. Confirmed, and they are already separate files.

- **Cheap pass — every run.** Filesystem walk, frontmatter parse, usage extraction, graph.
  Measured at 1.34s full parse, 0.42s with the substring prefilter. Rewrites `skills.json` whole.
  005 already ruled out an incremental scanner and nothing here reopens that.
- **Expensive pass — on demand only.** One batched LLM call writing `sidecar.json`. Its scope is
  much smaller than the library: plugin entries get Domain=Platform / Kind=Reference by rule
  (001), so the category pass only ever covers Eli's **169** global and repo skills, and the
  orchestration adjudication only covers the degree >= 2 candidates, which 006's slash-ref fix
  brings down to **25**. Today `sidecar.json` holds 198 entries against 426, and the 228 without
  coverage are all rule-categorized plugins.

The cheap pass never invokes the expensive one. It prints how many entries would need it.

**The scan must not delete sidecar entries whose `id` is missing from the current snapshot.**
Zero are stale today, but a skill that is renamed, moved, or briefly uninstalled would otherwise
lose a hand-checked category. Orphaned sidecar keys are kept and counted, not pruned.

### 3. A new skill appears immediately, marked uncategorized.

`category_status: "uncategorized"`, `domain` and `kind` null, and it sorts and filters like any
other row. 005 already specified that a missing sidecar entry never fails the scan; this ticket
adds the UI half: an **Uncategorized** option in the Kind control, so "what did I just add that
the library does not understand yet" is one click, and the count appears next to the snapshot
age. A new skill being invisible until an LLM pass runs would be the worst possible failure for
a tool whose whole purpose is finding forgotten skills.

### 4. Yes, the UI shows snapshot age, and warns at 14 days.

Rendered from `snapshot_generated_at`, which 005 already put in the envelope. Three states:

- under 14 days: quiet line, "Snapshot N days old".
- 14 days or more: warned state, with the exact command to run shown as copyable text.
- 30 days or more: the same warning plus a note that usage coverage is degrading, because
  transcripts are on a proven 30-day rolling delete (002) and a snapshot older than that is
  reporting a window that no longer exists on disk.

14 was chosen over a shorter threshold because skills arrive in bursts, not daily, and a banner
that is always yellow is a banner nobody reads.

### 5. Scope for the first build: the honesty, not the automation.

Ship: the age line with its three states, and the uncategorized count. Both are display over
fields that already exist. Do not ship: hooks, cron, a refresh command, or any incremental
scanning.

The condition for revisiting is Eli being annoyed by typing the command, not a date. Recorded
deliberately so that "008 said refresh was manual" does not later read as a permanent ban.

### Downstream effects

- **006 (UI):** adds two elements to the header — snapshot age with its threshold states, and the
  uncategorized count. Neither changes the data contract or reopens a closed question.
- **007 (publish):** publishing stays a separate deliberate command and is never triggered by a
  refresh. Confirmed from the other side.

Status: CLOSED 2026-08-18.
