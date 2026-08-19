# 002 — What counts as a "use", and how the usage columns behave

Parent: `../MAP.md`
Label: `wayfinder:research` (AFK)
Blocked by: none
Status: CLOSED 2026-08-18

## Question

Define exactly what the snapshot records for usage, and prove what is recoverable from the
transcript corpus.

Starting facts, already measured:

- 381 files in `~/.claude/projects/*/*.jsonl`. 177 `Skill` tool calls. 47 distinct skills.
- Per-call `timestamp` is present, so times-used and last-used both work.
- Corpus starts 2026-07-20. Roughly a 4 week window.

Research must establish:

1. Are there other ways a skill gets used that leave a different trace? Confirmed one already:
   hook-injected skills (`vercel-plugin` `UserPromptSubmit` injections) push skill content into
   context without a `Skill` tool call, so they read as unused. Find every such path
   (`SessionStart` hooks, `PreToolUse` injections, subagent invocations, `Task`/`Agent` calls
   naming a skill).
2. Do transcripts rotate, get pruned, or get compacted away? If so, on what schedule. This
   determines whether "0 uses" can ever be trusted.
3. How the three states are distinguished in the schema: used N times, confirmed never used,
   and no data available for this skill in the retained window.
4. Whether invocation *success* is distinguishable from invocation *attempt*.
5. Cost of the scan. 363MB of JSONL. Report actual scan wall time and whether incremental
   scanning (by file mtime) is needed or premature.

Answer with concrete numbers and the field list the snapshot should carry, not prose advice.

## Resolution

Resolved 2026-08-18 by direct measurement against the live filesystem. Every number below was
produced by a script run against `~/.claude`, not estimated. Where a claim is a negative ("leaves
no trace"), the negative was tested with a grep that returned zero and the test is named.

### Corpus baseline, re-measured

381 files matching `~/.claude/projects/*/*.jsonl`. The directory is 363 MB, but only 310.3 MB of
that is JSONL line content; the remainder is sibling non-JSONL material in the project folders.
107,949 total lines, **zero malformed lines** — the corpus is safe to parse strictly, with no need
for a lenient fallback path.

Record `type` distribution across the corpus:

| type | count |
| --- | --- |
| attachment | 46,287 |
| assistant | 25,461 |
| user | 16,360 |
| mode | 4,973 |
| last-prompt | 4,957 |
| ai-title | 3,413 |
| system | 2,036 |
| file-history-snapshot | 1,752 |
| permission-mode | 1,120 |
| file-history-delta | 1,120 |
| queue-operation | 443 |
| agent-name | 13 |
| pr-link | 8 |
| frame-link | 6 |

Two structural facts matter for the scanner. There are **zero records with `isSidechain: true`**
and **zero compaction records** (no `compact_boundary`, no `isCompactSummary`). Subagent
conversations are not written into these files at all, and nothing in the retained window has been
compacted, so no skill usage has been summarized away inside the window.

The ticket's starting figure of 177 `Skill` tool calls is off by one: the true count is **178**,
across **47 distinct raw skill identifiers**.

### 1. Every path by which skill content reaches a model

Six distinct paths were found. Only two of them produce a durable, machine-readable trace.

**Path A — `Skill` tool call.** An `assistant` record carrying a content block of
`type: "tool_use"`, `name: "Skill"`, with the skill identifier at `input.skill`. 178 occurrences,
47 distinct identifiers. Top counts: `grilling` 44, `agent-browser` 28, `prime` 18,
`plan-feature` 12, `grill-me` 7, `tdd` 7, `artifact-design` 4, then a long tail of 1-3.

The 47 raw identifiers are **not directly joinable to skill names on disk**. They arrive in three
shapes: bare (`grilling`), plugin-namespaced (`superpowers:brainstorming`,
`figma:figma-design-to-code`, `vercel-plugin:marketplace`, `posthog:querying-posthog-data`), and
occasionally slash-prefixed (`/grill-me`). Normalizing by stripping a leading `/` and everything
up to and including the last `:` resolves 47 raw identifiers down to 37 distinct real skills:
**19 personal, 20 plugin, 8 orphan**. The 8 orphans are `accessibility`, `artifact-design`,
`dataviz`, `execute`, `plan-feature`, `prime`, `run`, and `conductor:conductor`. Most are
Claude-Code-managed or built-in skills that have no directory under `~/.claude/skills` or
`~/.claude/plugins`; `conductor:conductor` belongs to a plugin that is no longer installed. The
snapshot must therefore carry an orphan bucket rather than silently discarding these, otherwise
usage records get thrown away whenever a plugin is uninstalled.

**Path B — hook-driven injection.** This is the confirmed path from the ticket, and it is far
larger and more structured than the ticket assumed. `vercel-plugin` v0.24.0 registers hooks across
seven events (`SessionStart`, `PreToolUse` on `Read|Edit|Write|Bash`, `PreToolUse` on `Agent`,
`UserPromptSubmit`, `PostToolUse` on `Bash`, `PostToolUse` on `Write|Edit`, `SubagentStart`,
`SubagentStop`, `SessionEnd`). Several of those write an HTML comment carrying a JSON payload into
the prompt context, and that comment is persisted in the transcript.

After deduplicating (the payload appears at several JSON escape depths on the same line, so a naive
regex sweep double-counts by roughly 2.7x), there are **2,100 injection events** in six classes:

| marker / event | events |
| --- | --- |
| `skillInjection` / `UserPromptSubmit` | 1,120 |
| `skillInjection` / `PostToolUse:Read` | 638 |
| `skillInjection` / `PostToolUse:Bash` | 171 |
| `skillInjection` / `PostToolUse:Edit` | 122 |
| `postValidation` / `posttooluse-validate` | 66 |
| `skillInjection` / `PostToolUse:Write` | 48 |

The trace patterns are stable and worth writing down exactly. The `UserPromptSubmit` form:

```
<!-- skillInjection: {"version":1,"hookEvent":"UserPromptSubmit","matchedSkills":["agent-browser-verify","agent-browser","investigation-mode","nextjs","ai-sdk"],"injectedSkills":["ai-sdk","nextjs"],"summaryOnly":[],"droppedByBudget":[]} -->
```

The `PostToolUse` form swaps `hookEvent` for `toolName` plus `toolTarget`, and adds `reasons` and
sometimes `verificationId`:

```
<!-- skillInjection: {"version":1,"toolName":"Edit","toolTarget":"/Users/.../career-partner-sidebar.tsx","matchedSkills":["react-best-practices"],"injectedSkills":[...],"summaryOnly":[],"droppedByBudget":[],"reasons":[...]} -->
```

The validation form is a different shape again:

```
<!-- postValidation: {"version":1,"hook":"posttooluse-validate","filePath":"/Users/.../users/page.tsx","matchedSkills":["next-cache-components","next-forge","nextjs"],"errorCount":0,"recommendedCount":1,"warnCount":...,"chainedSkills":[...]} -->
```

Four observed key-shapes in total, all carrying `version: 1`. The scanner should key off
`matchedSkills` / `injectedSkills` presence rather than the marker name, and should tolerate an
unknown `version` by recording the event and flagging it, not by crashing.

Two secondary markers wrap the same payloads and are useful as anchors but carry no skill names
themselves: `<!-- marker:review-injected -->` (56) and
`<!-- marker:dev-server-verify iteration="1" max="2" -->` (54). A `skillUpgrade` marker
(22 occurrences) appears nested inside `postValidation` output and records a skill-to-skill
redirect, e.g. `{"from":"vercel-functions","to":"observability","line":141}`. That is a
recommendation, not a use, and should not be counted.

Path B covers **39 distinct skills, 3,794 injections**. Crucially, **32 of those 39 have no other
signal of any kind** and would read as never-used under a Skill-tool-call-only scan: `nextjs`,
`react-best-practices`, `next-cache-components`, `vercel-services`, `ai-sdk`, `verification`,
`chat-sdk`, `auth`, `shadcn`, `ai-elements`, `sign-in-with-vercel`, `runtime-cache`,
`vercel-flags`, `investigation-mode`, `json-render`, `vercel-queues`, `bootstrap`, `workflow`,
`agent-browser-verify`, `next-upgrade`, `vercel-storage`, `ai-gateway`, `vercel-functions`,
`vercel-agent`, `next-forge`, `vercel-api`, `deployments-cicd`, `observability`,
`routing-middleware`, `vercel-cli`, `turborepo`, `turbopack`, `env-vars`, `v0-dev`, `marketplace`,
`vercel-sandbox`, `cron-jobs`, `knowledge-update`. `nextjs` alone was injected 396 times and has
zero `Skill` tool calls.

**Path C — slash command typed by the user, recorded only in `~/.claude/history.jsonl`.** This was
not in the ticket and is the single most valuable discovery. `history.jsonl` is a flat JSONL of
5,402 records with a uniform shape:
`{"display","pastedContents","project","sessionId","timestamp"}`, where `timestamp` is epoch
milliseconds. 87 distinct slash-command names appear in `display`. It spans **2026-03-04 to
2026-08-18, 167 days** — 5.6x the transcript window — and it is monotonically appended, with
records in every month (Mar 362, Apr 742, May 470, Jun 1,692, Jul 1,532, Aug 604).

Path C is not merely a longer view of Path A; it is a genuinely different mechanism. Restricting
`history.jsonl` to the transcript window (>= 2026-07-20) yields 18 personal skills, and Path A
yields 18 personal skills, but they overlap on only 8. Ten personal skills appear in the history
window with no `Skill` tool call (`ask-matt`, `daily-reflection`, `e2e-test`, `fact-checker`,
`find-skills`, `handoff`, `implement`, `review`, `week-wrap`, `zoom-out`), and ten appear as a
`Skill` tool call but never in the typed history (`agent-browser`, `brand-workshop`, `code-review`,
`codebase-design`, `grilling`, `humanizer`, `meeting-agenda`,
`sanity-portable-text-conversion`, `tdd`, `to-issues`). A typed slash command frequently resolves
without ever emitting a `Skill` tool_use, so the two sources must be unioned. Magnitude of the
undercount, same corpus: `prime` 18 tool calls vs 146 typed; `execute` 3 vs 92; `feature-sprint`
3 vs 76; `impeccable` 2 vs 21; `improve-codebase-architecture` 1 vs 18; `bug-detective` 3 vs 17.

Path C also carries noise that must be filtered rather than trusted. Of the 87 names, 46 match no
skill on disk. They fall into built-in CLI commands (`clear` 662, `mcp` 52, `model` 32, `login`,
`doctor`, `plugin`, `resume`, `settings`, `voice`, `tui`, `effort`, `memory`, `context`), typos
(`bug-detecthive`, `excute`, `clearcan`, `using-superpowe`, `algorihmic-art`), and mangled paste
artifacts where a file path got glued onto the command. The scanner must therefore **inner-join
history names against the known skill-name set and drop non-matches**, never fuzzy-match. The cost
is that a typo'd invocation is a real use that gets dropped; that is acceptable and should be
recorded as a known undercount.

**Path D — `SubagentStart` hook injection. No trace. Confirmed empirically.** `vercel-plugin`
registers `subagent-start-bootstrap.mjs` on `SubagentStart` with matcher `.+`, and it injects full
skill bodies into a subagent's context wrapped in
`<!-- vercel-plugin:subagent-bootstrap agent_type="..." budget="..." -->` and
`<!-- skill:vercel-services --> ... <!-- /skill:vercel-services -->`. This was verified live: the
research agent that resolved this ticket received exactly that injection. Yet grepping the entire
381-file corpus for `subagent-bootstrap` returns **0**, and for `<!-- skill:` returns **0**. Since
there are also zero `isSidechain: true` records, subagent context is never persisted to disk. This
path is **permanently unrecoverable**. It is not a small path: 114 `Task`/`Agent` calls were made
in the window (78 `general-purpose`, 23 `Explore`, 13 with no `subagent_type`), and each one fired
the bootstrap hook.

**Path E — `SessionStart` seen-skills replay. No trace.** `session-start-seen-skills.mjs` runs on
`SessionStart` (matcher `startup|resume|clear|compact`) and replays previously-seen skills into the
new session. Greps for `session-start-seen-skills`, `seenSkills`, and the plugin's banner string
`Vercel plugin active` all return **0** across the corpus. Its backing state is per-session and
ephemeral: files named `vercel-plugin-<session>-<scopeId>-seen-skills.{d,txt}` in the session
temp area, explicitly deleted by `session-end-cleanup.mjs`. Confirming this, all six
`~/.claude/plugins/data/*` plugin state directories are **empty**. Not recoverable.

**Path F — a skill's content being read directly** (`Read` on a `SKILL.md`, or `cat`ing it in
`Bash`). Recoverable in principle from `tool_use` inputs, but this is skill *authoring* traffic,
not skill *use*. Recommend excluding it and saying so, otherwise `skill-creator` work inflates the
usage of every skill Eli has recently edited.

**Rejected: free-text name matching.** Tested and it is fatal. All **167 of 167** real personal
skill names appear as free text in at least one transcript, **152 appear in 50 or more**, and 12
(`video`, `social`, `sms`, `schema`, `research`, `pricing`, `offers`, `image`, `frontend-design`,
`cro`, `aso`, `analytics`) appear in all 381. The cause is the available-skills roster that Claude
Code prints into the system prompt every session, which also produces ~736-773 hits each for
namespaced strings like `vercel-plugin:nextjs`. **123 personal skills have zero structured signal
yet still appear as free text.** A substring scan would report ~100% usage and be worthless. Only
structured extraction — `tool_use.input.skill`, the `skillInjection`/`postValidation` JSON, and
`history.jsonl` `display` — may be used.

### 2. Retention: transcripts are deleted on a rolling 30-day window

This is settled, and it means **"0 uses" can never be read as "never used"** from transcripts
alone.

Neither `settings.json` nor `settings.local.json` sets `cleanupPeriodDays`; `settings.local.json`
contains only a `permissions` key and no hooks at all. Claude Code's default retention therefore
applies. The evidence that it is actively enforced:

- `~/.claude/.last-cleanup` contains `2026-08-18T19:48:16.657Z` — cleanup ran today.
- A histogram of all 381 file mtimes by age in days has a **hard cutoff at 29** and nothing beyond
  it: ages 0-29 are populated (heaviest at 26 with 59 files and 27 with 40 files), and 30+ is
  empty. Interior gaps at 9, 16, and 23 days are simply days Eli did not work.
- Oldest surviving file mtime is 2026-07-20T11:35:49; newest is 2026-08-18T14:54:07.

Deletion is whole-file by mtime, not truncation. No file showed signs of truncation, and the zero
malformed lines across 107,949 lines confirms nothing is being cut mid-record. A long-running
session survives as long as it keeps being appended to, which means the window is slightly ragged
at the edge rather than a clean 30-day cut.

`history.jsonl` is **not** subject to this cleanup — it holds 167 days and grows monotonically. It
is the only long-horizon usage source on the machine and should be treated as the primary evidence
for "has Eli ever used this", with transcripts supplying richer detail for the last 30 days.

Everything else was checked and holds no skill usage data: `stats-cache.json` (already known),
`~/.claude/sessions` (two session JSONs plus key files, no skill data), `~/.claude/data`
(a `chat.db` plus logs for the second-brain bot), `~/.claude/tasks` (todo items only — grep for
`skill` returns nothing), `~/.claude/telemetry` (two `1p_failed_events.*.json` files containing
`tengu_event_loop_stall` events, zero occurrences of `skill`), and `~/.claude/plugins/data`
(all six directories empty).

### 3. Scan cost: incremental scanning is premature

Timed on this machine, warm page cache, single-threaded Python 3.9:

| approach | wall seconds |
| --- | --- |
| raw byte read of all 310.3 MB | 0.03 |
| substring prefilter then parse matching lines | 0.42 |
| full `json.loads` on every line plus regex sweep | 1.34 |
| the full three-source cross-reference used for this ticket | 1.16 |
| `grep -ac` prefilter across all 381 files | 0.01 |

**Full scan is 1.34 seconds at the pessimistic end.** Even assuming a fully cold cache and a
conservative 200 MB/s sequential read, I/O adds under 2 seconds. Recommendation: **scan everything,
every time. Do not build mtime-based incremental scanning.** It would add a cache file, an
invalidation bug surface, and a staleness mode, to save one second. This is exactly the Ponytail
ladder's "does this need to be built at all" rung. Revisit only if the corpus exceeds roughly
3 GB, which at the current ~12 MB/day accrual against a 30-day rolling delete it will never do —
the transcript corpus is effectively size-stable. `history.jsonl` grows unboundedly but is 1.4 MB
after 167 days.

Two implementation notes that matter more than incrementality. First, prefilter with a substring
test (`'Skill' in line or 'skillInjection' in line`) before `json.loads`; that alone is the
difference between 1.34 s and 0.42 s. Second, deduplicate injection payloads by
`(file, line_number, canonical_json)` — the same payload is embedded at multiple escape depths and
a naive sweep inflates counts 2.7x (5,788 raw matches vs 2,165 real events).

### 4. Invocation success vs attempt

**Not meaningfully distinguishable for Path A, and the schema should not pretend otherwise.**
All 178 `Skill` tool_use blocks have a matching `tool_result`, so there are **zero orphaned or
interrupted attempts**. Of those 178 results, **`is_error` is `true` zero times** — while the
corpus does contain 471 `is_error: true` results across other tools, so the field is genuinely
exercised elsewhere. No `Skill`-specific failure text exists anywhere either: greps for
"skill not found", "does not exist", and Skill permission-denial phrasings all return 0. In this
corpus, attempt equals success.

The useful distinction lives in Path B instead, and it is real: the injection payloads separate
`matchedSkills` (the skill was ranked as relevant) from `injectedSkills` (its content was actually
delivered). Across 2,100 events there are 8,519 matches but only 3,794 injections — **55.5% of
matches were considered and not delivered**. Top considered-but-not-delivered: `nextjs` 900,
`ai-sdk` 573, `vercel-services` 510, `next-cache-components` 444, `json-render` 231,
`verification` 205. `summaryOnly` and `droppedByBudget` are present in every payload but are
**empty in all 2,100 events** in this corpus, so they should be read and stored but not surfaced
in the UI yet.

Design consequence: model "considered" and "delivered" as separate counters on the injected path,
and do not model a success/failure flag on the tool-call path. Carry `attempt_count` only as an
`is_error` tally that is currently always zero, so a future failure becomes visible rather than
silently folded into successes.

### Coverage this contract actually achieves

Measured against the real skill inventory. `~/.claude/skills` has 172 directories but only **167
contain a `SKILL.md`**; the other five are scaffolding workspaces (`creator-content-workspace`,
`daily-reflection-workspace`, `design-accelerator-workspace`, `discovery-sprint-workspace`,
`project-plan-builder-workspace`) and must be excluded from the library. The MAP's figure of 172
is a directory count, not a skill count. Separately, the 1,190 plugin `SKILL.md` files collapse to
only **239 distinct skill names** once duplicate cached plugin versions are folded together, which
ticket 004 will need.

Personal skills (out of 167) with at least one signal:

| source | personal skills covered |
| --- | --- |
| A — `Skill` tool call | 18 |
| B — hook injection | 1 |
| C — `history.jsonl` slash | 35 |
| **union of A+B+C** | **44** |

Over the combined personal + plugin name space of 410 distinct names: A covers 26, B covers 39,
C covers 41, union **88 of 410 (21.5%)**, leaving **322 with no signal at all**. Adding Path C more
than doubles personal coverage over the ticket's assumed baseline (18 to 44), and Path B rescues 32
plugin skills from a false "never used" verdict. The honest headline is that **roughly four out of
five skills on this machine have no recoverable usage evidence**, and the UI must present that as
absence of evidence rather than evidence of absence.

### Snapshot field list for usage

One `usage` object per skill entry. Types are JSON types; `null` is load-bearing and distinct from
`0` throughout.

| field | type | null semantics |
| --- | --- | --- |
| `usage.state` | string enum | never null. One of `"used"`, `"never_used"`, `"no_data"`. |
| `usage.total_count` | integer \| null | `null` iff `state == "no_data"`. `0` iff `state == "never_used"`. Sum of `tool_calls + injections + slash_commands`. |
| `usage.last_used_at` | ISO 8601 UTC string \| null | `null` when `total_count` is `0` or `null`. Max timestamp across all contributing sources. |
| `usage.first_seen_at` | ISO 8601 UTC string \| null | Earliest observed use. Same null rule. Useful for distinguishing a long-dormant skill from a brand-new one. |
| `usage.days_since_last_use` | integer \| null | Derived at scan time from `snapshot_generated_at`, not from wall clock at render time. `null` mirrors `last_used_at`. |
| `usage.tool_calls` | integer | Path A count after name normalization. Always present, `0` when none. |
| `usage.tool_calls_last_at` | ISO 8601 \| null | |
| `usage.tool_call_errors` | integer | `is_error: true` tally on Path A. Currently `0` for every skill. |
| `usage.injections` | integer | Path B `injectedSkills` count, deduplicated. `0` when none. |
| `usage.injections_last_at` | ISO 8601 \| null | |
| `usage.injection_considered` | integer | Path B `matchedSkills` count. Always `>=` `injections`. |
| `usage.injection_summary_only` | integer | From `summaryOnly`. `0` across this whole corpus. |
| `usage.injection_dropped_by_budget` | integer | From `droppedByBudget`. `0` across this whole corpus. |
| `usage.slash_commands` | integer | Path C count from `history.jsonl`, after inner-join on known names. `0` when none. |
| `usage.slash_commands_last_at` | ISO 8601 \| null | |
| `usage.sources` | array of string | Subset of `["tool_call","injection","slash_command"]`, empty array when no signal. Lets the UI say *why* a skill counts as used. |
| `usage.evidence_window_start` | ISO 8601 | Earliest timestamp the scan could have seen for this skill: `min(transcript_window_start, history_window_start)` for Path C-capable skills. Makes the horizon explicit per row. |
| `usage.coverage` | string enum | `"full_history"` when Path C could have observed this skill across the entire 167-day history, `"transcripts_only"` when the only possible evidence is inside the 30-day transcript window. Drives the `no_data` vs `never_used` decision below. |
| `usage.orphan` | boolean | `true` when usage records were found under a normalized name that matches no skill currently on disk. Such records live in a top-level `orphan_usage` array, not on a skill entry. |
| `usage.name_aliases` | array of string | Raw identifiers folded into this entry, e.g. `["vercel-plugin:nextjs","nextjs"]`. Needed for auditing the normalization. |

Top-level snapshot metadata that the usage fields depend on, and without which the null semantics
are unreadable:

| field | type | notes |
| --- | --- | --- |
| `snapshot_generated_at` | ISO 8601 | Anchor for every `days_since_*`. |
| `usage_sources.transcripts.file_count` | integer | 381 at time of writing. |
| `usage_sources.transcripts.window_start` | ISO 8601 | 2026-07-20. Recomputed each scan. |
| `usage_sources.transcripts.window_end` | ISO 8601 | |
| `usage_sources.transcripts.retention_days` | integer \| null | `30` inferred from default; `null` if `cleanupPeriodDays` is ever set to something unreadable. Record whether it was read from settings or inferred. |
| `usage_sources.history.window_start` | ISO 8601 | 2026-03-04. |
| `usage_sources.history.record_count` | integer | 5,402. |
| `usage_sources.unrecoverable_paths` | array of string | `["subagent_start_injection","session_start_seen_skills"]`. Surfaced in the UI as a standing caveat. |
| `orphan_usage` | array of objects | `{raw_name, normalized_name, counts, last_used_at}` for the 8 orphans. |

**The three-state rule, stated precisely.** This is the decision the ticket asked for.

- `state = "used"` when `total_count > 0`.
- `state = "never_used"` when `total_count == 0` **and** `coverage == "full_history"` — that is,
  the skill's name is one that a typed slash invocation would have recorded in `history.jsonl`, and
  167 days of that file contain no such record. This is the only defensible "never".
- `state = "no_data"` when `total_count == 0` **and** `coverage == "transcripts_only"` — the only
  evidence channel available for this skill is the 30-day transcript window, so silence proves
  nothing.

In practice almost every personal skill qualifies for `full_history` because Eli invokes them by
slash command, which is why Path C is what makes a trustworthy "never used" possible at all.
Plugin skills reached only by hook injection fall into `transcripts_only` and can only ever be
reported as `no_data`. The UI should render `never_used` and `no_data` differently — "never used in
167 days" versus "no usage data" — and must never collapse them into a single zero, because that
collapse is precisely the error that would make the tool lie about 322 skills.
