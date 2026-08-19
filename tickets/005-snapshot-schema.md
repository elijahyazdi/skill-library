# 005 — The snapshot schema and the scan contract

Parent: `../MAP.md`
Label: `wayfinder:grilling` (HITL)
Blocked by: 001, 002, 003, 004
Status: CLOSED 2026-08-18

## Question

Lock the shape of `skills.json` and the contract of the script that produces it.

Depends on the four upstream tickets for: category field shape (001), usage fields and their
no-data state (002), orchestration field (003), entry key and provenance (004).

Must decide:

1. The full field list per entry, with types and null semantics.
2. Whether the inferred sidecar (category, orchestration) is a separate file merged at scan time
   or folded into the single output. Separate keeps the expensive LLM pass independent of the
   cheap filesystem scan.
3. Where the snapshot and sidecar live on disk, relative to the app.
4. What the scan does when a skill is new and has no sidecar entry yet. Fail, or show as
   uncategorized?
5. Whether the snapshot carries a generated-at timestamp and corpus window, so the UI can be
   honest about staleness.
6. Language for the scan script. Python 3 is already present and has YAML available; Node is
   also present. Ponytail says pick one and write one file.

## Resolution

Resolved 2026-08-18 by data-modeling session. All six questions answered, plus the plugin count
reconciliation the map handed down. Disk was re-measured rather than trusting the map's figures.

### 0. The population, re-measured (the reconciliation the map demanded)

The map recorded two irreconcilable plugin counts: 259 (ticket 004, enumerated from
`installed_plugins.json`) and 239 (ticket 002, distinct names). Both are wrong, and for the same
reason: a recursive `installPath/**/SKILL.md` walk over-collects 29 files that are not skills.

- 23 are `skills/<name>/upstream/SKILL.md` vendored copies inside `vercel@claude-plugins-official`
  and `vercel-plugin@vercel-vercel-plugin`.
- 4 are a nested `plugins/caveman/skills/` copy of the same repo inside `caveman@caveman`.
- 2 are `workflow-skills/generate-project-plan` and `workflow-skills/video-interaction-mapper`
  inside `figma@claude-plugins-official`. Neither appears in the harness skill roster.

The enumeration rule is therefore **exactly one level: `installPath/skills/*/SKILL.md`**. The same
rule is required for the global root, where a recursive walk picks up
`design-accelerator-workspace/skill-snapshot-old/SKILL.md`.

Measured with the one-level rule:

| Segment | Count | Notes |
| --- | --- | --- |
| Plugin skills | **257** | 12 enabled plugins contribute skills; `swift-lsp@claude-plugins-official` is enabled and contributes none. Distribution: posthog 137, vercel-plugin 39, vercel 30, superpowers 14, figma 12, sentry 8, caveman 7, visual-critique 4, supabase 2, paper-desktop 2, playground 1, skill-creator 1. |
| Global skills | **167** | 173 directories; excluded are `.git` and five `*-workspace` scaffolds. Confirms 004. |
| Repo-only skills | **2** | `algorithmic-art` and `reflect` in `~/Development/claude-skills`. |
| **Total entries** | **426** | |

**Rows are files, not names.** 232 distinct plugin names exist; 25 collide across `vercel` and
`vercel-plugin`. Both plugins are enabled and both variants are independently invocable, so
name-deduplication would delete a real, reachable skill from the library. The unique key stays the
absolute directory path per 004, and the display `id` disambiguates the collisions.

### 1. Two files, not one

`skills.json` is written by the scanner on every run. `sidecar.json` holds only what a judgment call
produced and what costs money to regenerate. A third file, `overrides.json`, holds hand corrections.

| | `skills.json` | `sidecar.json` | `overrides.json` |
| --- | --- | --- | --- |
| Author | `scan.py`, every run | one batched LLM call | Eli, by hand |
| Cost to regenerate | 0.42 s | tokens | attention |
| Fields | everything mechanical, including the orchestration graph | `domain`, `domain_secondary`, `kind`, `orchestration_class`, `orchestration_reason` | any sidecar field, plus `publishable` |
| Keyed on | `path`, with `id` as the display key | `id` | `id` |

Folding the sidecar into the snapshot was rejected: a rescan would either clobber the categories or
force the LLM pass to run on every scan. Writing categories into skill frontmatter was rejected by
locked decision 1 in the map, which makes the tool read-only with respect to `SKILL.md`.

**Merge order is `skills.json`, then `sidecar.json`, then `overrides.json`. Overrides last.**

**Correction to ticket 003.** 003 specified the orchestration override map as "keyed by skill name".
Bare name collides on 96 names across 206 files (004), so a name-keyed sidecar would apply one
skill's adjudication to another. Both the sidecar and the overrides file key on `id`.

### 2. Disk layout

Four files, no build step, no dependency beyond PyYAML which is already installed.

```
wayfinder/
  index.html          the app; opens with `open index.html`
  scan.py             the scanner
  data/
    skills.json       generated, ~426 entries
    sidecar.json      generated by the LLM pass, re-runnable
    overrides.json    hand-maintained, expected to hold ~12 entries
```

`data/` is relative to `index.html` so the same fetch path serves local and published use, per
locked decision 3 in the map.

### 3. A new skill never fails the scan

A skill absent from the sidecar gets `category_status: "uncategorized"` and null category fields.
Failing was rejected outright: adding a skill would break the tool, which inverts the tool's purpose.
Uncategorized entries are visible by default and filterable, so the state is a prompt to re-run the
LLM pass rather than a silent hole.

### 4. Timestamps and corpus windows: yes

Already forced by 002. Every `days_since_*` value anchors on `snapshot_generated_at` computed at scan
time, never on wall clock at render time, so a stale snapshot reports stale numbers consistently
rather than drifting. The UI additionally computes `snapshot_age_days` at render from
`snapshot_generated_at` and surfaces it, which is what makes ticket 008 optional for the first build.

### 5. Language: Python 3, one file

PyYAML 6.0.3 is present, so no new dependency. 004 measured the alternative and it loses decisively:
regex frontmatter parsing fails outright on only 2 files but **silently returns the wrong description
on 606**, because `description: |` and `description: >` block scalars make it capture the sigil. The
hybrid of PyYAML plus a force-quote repair pass measured 1375 clean, 21 repaired, 3 fallback.

### 6. Bodies are never inlined

Measured on the prior art: `~/Development/claude-skills/skills.json` is **819 KB for 42 skills**,
because it carries `body` and a duplicate `fullContent`. Extrapolated to 426 entries that is roughly
8 MB of JSON the browser must parse before rendering a single row. The snapshot carries `description`
and `body_lines` only. A row's action is handing over a file path, not displaying the body.

This also settles the map's open question about that file: the 42-entry `skills.json` and its
`index.html`, generated by `.github/workflows/build-skills.yml`, are **retired, not extended**. Its
schema (`name, description, folder, path, slug, body, fullContent`) shares no field semantics with
this one, its key is a bare relative folder name, and its scope is a 42-skill subset. It stays in
place as a working reference for the static-page-plus-JSON stack, which it proves at 781 lines of
dependency-free HTML.

---

## The schema

Types are JSON types. `null` is load-bearing throughout and never interchangeable with `0` or `""`.

### Top-level snapshot object

| Field | Type | Notes |
| --- | --- | --- |
| `schema_version` | integer | `1`. Bump on any breaking field change so the UI can refuse a snapshot it cannot read. |
| `snapshot_generated_at` | ISO 8601 UTC | Anchor for every `days_since_*`. |
| `scanner_version` | string | Git-free; a hand-bumped constant in `scan.py`. |
| `counts` | object | `{entries, global, plugin, repo, builtin, uncategorized, orphan_usage}`. Lets the UI assert its row count matches. |
| `roots` | array of object | `{root, source, rule}` for each scanned root, recording the one-level glob actually used. |
| `plugins` | array of object | `{key, name, marketplace, version, install_path, last_updated, skill_count, enabled}` for each entry in `installed_plugins.json` gated on `enabledPlugins`. Includes enabled plugins with zero skills, so `swift-lsp` is visible as deliberately empty rather than missing. |
| `command_vocabulary` | array of string | The 11 names under `~/.claude/commands`. Required by 003 for correct graph resolution. **Not** library rows, per 004. |
| `usage_sources` | object | Per 002: `transcripts.{file_count, window_start, window_end, retention_days, retention_source}`, `history.{window_start, window_end, record_count}`, `unrecoverable_paths`. |
| `orphan_usage` | array of object | `{raw_name, normalized_name, counts, last_used_at}`. Usage records matching no skill on disk. Deliberately dangling; never silently discarded. |
| `scan_errors` | array of object | `{path, stage, error}`. Empty array is the normal case. Distinct from `parse_status`, which covers a file that was read but parsed badly. |
| `entries` | array of object | The 426 skill entries below. |

### Skill entry

Identity and provenance, from 004:

| Field | Type | Notes |
| --- | --- | --- |
| `path` | string | Absolute skill directory. The unique key. |
| `skill_file` | string | `path + "/SKILL.md"`. |
| `id` | string | Display and join key. `<name>` global, `<plugin>:<name>` plugin, `repo:<name>` repo-only. |
| `name` | string | Directory basename, always. |
| `declared_name` | string \| null | Frontmatter `name` when present and different. Diagnostic only; disagrees on 8 entries. |
| `description` | string | Frontmatter `description` via PyYAML with repair fallback. Never truncated at parse time. |
| `source` | enum | `global` \| `plugin` \| `repo` \| `builtin`. |
| `plugin` | string \| null | `name@marketplace`. |
| `marketplace` | string \| null | Segment after `@`. |
| `plugin_version` | string \| null | |
| `version` | string \| null | Frontmatter `metadata.version`, then top-level `version`, then `plugin_version`. **`null` when unknown**, amended from 004's `"unknown"` string. |
| `author` | string | Precedence: frontmatter `metadata.author`, `plugin.json` `author.name`, `marketplace.json` `owner.name`, `.skill-lock.json` source owner, then `"Eli"`. |
| `author_source` | enum | `frontmatter` \| `plugin` \| `marketplace` \| `skill-lock` \| `assumed`. |
| `upstream_url` | string \| null | `.skill-lock.json` `sourceUrl` or `plugin.json` `repository`. |
| `updated_at` | ISO 8601 \| null | `.skill-lock.json` `updatedAt` for the 84 symlinked global skills, `installed_plugins.json` `lastUpdated` for plugins. **`null` when unknown**, amended from 004's `"unknown"` string. File mtimes are bulk-copy stamps and are never used. |
| `is_symlink` | boolean | Resolves into `~/.agents/skills/`. |
| `also_in_repo` | boolean | Same-named directory exists in `~/Development/claude-skills`. |
| `repo_differs` | boolean | The two `SKILL.md` files differ. True for 8 of 40 overlaps. |
| `model_invocable` | boolean | False when frontmatter sets `disable-model-invocation: true`. 22 of 167. |
| `parse_status` | enum | `ok` \| `repaired` \| `fallback`. |
| `body_lines` | integer | Cheap size signal for the later "needs refinement" work. |
| `has_resources` | boolean | Directory contains any of `references/`, `scripts/`, `agents/`, `assets/`, `evals/`. |

**Why `version` and `updated_at` became nullable.** 004 specified the string `"unknown"`. That mixes
a sentinel into a field the UI must sort as a date, and the map's proposed default view is sorted by
recency. A string sentinel sorts as a string. Null sorts as absent and the UI renders the word.

Category, from 001, merged from the sidecar:

| Field | Type | Notes |
| --- | --- | --- |
| `domain` | string \| null | One of the 8 domains. `null` displays as `Any` and means universal, not unknown. |
| `domain_secondary` | string \| null | Recorded and displayed, never filtered on. |
| `kind` | enum | Required, single, one of the 7 Kinds. Tiebreak precedence `Orchestrator > Ritual > Converter > Reviewer > Generator > Thinking tool > Reference`. |
| `category_source` | enum | `rule` \| `llm` \| `override` \| `none`. 001 fixed the merge order but specified no provenance; without this the UI cannot mark a value as machine-guessed. |
| `category_status` | enum | `assigned` \| `uncategorized`. Per decision 3 above. |

Orchestration, from 003. Mechanical fields in `skills.json`, adjudication from the sidecar:

| Field | Type | Notes |
| --- | --- | --- |
| `orchestration_degree` | integer | Distinct outbound references. Rendered as a count on the row, never as a filter. |
| `delegates_to` | array of string | Raw names as written in the body. Load-bearing as UI evidence: it is what makes 0.71 precision acceptable. |
| `delegates_to_ids` | array of string | Resolved `id` values. |
| `delegates_to_unresolved` | array of string | Names matching no skill and no command. Kept rather than dropped, so precision stays inspectable. |
| `reached_via` | array of string | Resolved ids of orchestrators naming this skill. Empty for standalone. Drives the "never reached on its own" filter, which 003 found is the strongest field in the model. |
| `orchestration_verdict` | boolean | 003's cheap rule: `degree >= 2 AND (frontmatter orchestrat\|sequenc\|sub-skill OR refs across 2+ Step/Phase sections)`. Precision 0.71, recall 0.86. The pre-adjudication default. |
| `orchestration_class` | enum \| null | `orchestrator` \| `router` \| `leaf`. Null until the batched LLM call over the `degree >= 2` candidates runs. |
| `orchestration_source` | enum | `rule` \| `adjudicated` \| `override`. |

Footer-stripping is load-bearing when computing these: `pm-skills` stamps a Dependencies footer on
every leaf, which inflates roughly 30 leaves to four references each. Fenced code and terminal
next-step blocks are excluded too. The name vocabulary is skill directories plus
`command_vocabulary` plus plugin commands.

Usage, from 002. The full 21 fields stand as specified in that ticket, with two additions:

| Field | Type | Notes |
| --- | --- | --- |
| `usage.attribution` | enum | `exact` \| `ambiguous`. |
| `usage.attribution_candidates` | array of string \| null | Null when `exact`. The competing ids when `ambiguous`. |

**Why attribution had to be added.** 002 joins usage to entries on a normalized name. Skill tool
calls carry the plugin prefix (`vercel:nextjs`), but hook-injection payloads carry the bare name
(`nextjs`), and `nextjs` has 396 injections and two candidate entries. No field in 002 records that
the attribution is a guess. The rule: **an ambiguous count is written to every candidate entry and
flagged**, because suppressing it would report a heavily-used skill as unused, and splitting it would
invent a number. The consequence is that **library-wide usage totals must never be summed across
entries**, which is acceptable given the map puts charts out of scope.

Publishing, reserved for 007:

| Field | Type | Notes |
| --- | --- | --- |
| `publishable` | boolean | 007 owns the rule and may replace this with an explicit allowlist. Default deny where `domain == Personal`, per 001. Reserved here so 007 does not force a schema version bump. |

CTA rows, documented for the UI ticket rather than stored:

| CTA | Object | Notes |
| --- | --- | --- |
| Open in editor | Skill | On `skill_file`. This is the tool's primary action; read-only means handing over a path. |
| Copy invocation | Skill | `/name` or `/plugin:name` from `id`. |
| Open upstream | Skill | On `upstream_url` when non-null. 343 of 426 entries have a derivable author, fewer have a URL. |
| Re-run scan | Snapshot | Surfaced next to `snapshot_age_days`. |

### Scan contract

1. Enumerate roots with the one-level rule. Global: `~/.claude/skills/*/SKILL.md`, excluding `.git`
   and `*-workspace` by path-prefix rule. Plugin: for each key in `installed_plugins.json` `plugins`
   gated on `settings.json` `enabledPlugins`, glob `installPath/skills/*/SKILL.md`. Repo:
   `~/Development/claude-skills/*/SKILL.md`, kept only where the name is absent from global.
   Never walk `~/.claude/plugins` directly; that is what pulls in 678 stale cache duplicates and
   the catalog-only marketplaces.
2. Read four side files: `installed_plugins.json`, `known_marketplaces.json`, each live plugin's
   `plugin.json`, and `~/.agents/.skill-lock.json`.
3. Parse frontmatter with PyYAML plus force-quote repair. Record `parse_status`.
4. Mine usage: `history.jsonl` first as the primary source across its full 167-day window, then
   transcripts within the 30-day retention window. Substring-prefilter before `json.loads`; dedupe
   injection payloads by `(file, line, canonical_json)` because nested escaping inflates raw counts
   2.7x. Structured extraction only; free-text name matching is rejected as fatal.
5. Compute the reference graph over all entries with footers, fences, and next-step blocks stripped.
   Resolve to ids; keep unresolved names.
6. Apply the three-state usage rule: `used` when `total_count > 0`; `never_used` when `0` and
   `coverage == "full_history"`; `no_data` when `0` and `coverage == "transcripts_only"`.
7. Write `data/skills.json`. Never write to any `SKILL.md`.

No incremental scanner. 002 measured a full parse at 1.34 s and a prefiltered parse at 0.42 s.

### Known holes this schema does not close

- **Built-in skills.** Roughly 14 harness skills (`design`, `dataviz`, `artifact-design`, `simplify`,
  `loop`, `schedule`, `run`, `security-review` and others) exist in no scanned root. `source` reserves
  a `builtin` value and `counts.builtin` reserves a slot, both empty today. Populating them requires a
  hardcoded list, which is a decision for whoever builds the scanner, not a schema question.
- **Structurally unrecoverable usage.** `SubagentStart` bootstrap injection leaves no trace, and 55%
  of hook matches are considered but never delivered. `usage_sources.unrecoverable_paths` names the
  channels; how the UI says so is 006's call.
- **A `router` Kind.** 001 closed with 7 Kinds; 003 found `ask-matt` sits outside the
  orchestrator/leaf binary. `orchestration_class` carries `router` independently of `kind`, so 001
  does not need reopening for one skill.
- **`pm-skills` categories.** Their `marketplace.json` carries per-skill `category` and `tags`, so if
  those 55 are ever installed, `category_source` would read `rule` for them at no LLM cost. Currently
  catalog-only and excluded.

### Downstream effects

- **006 (UI):** unblocked. Sizing is **426 rows, not 1362**. `reached_via` is the field 003 flagged as
  most likely to change behaviour, so the "never reached on its own" filter deserves a place in the
  default view rather than a drawer. The prior `index.html` at 781 dependency-free lines is evidence
  the static-page stack holds; the snapshot without bodies is the reason it will stay fast.
- **007 (publish):** `publishable` exists, and the second-command architecture the ticket suspects is
  correct is now cheap, because the filtered snapshot is the same writer with an entry filter.
- **008 (refresh):** unblocked, and lower priority than the map assumed. `snapshot_generated_at` plus
  a rendered `snapshot_age_days` makes "re-run the script" honest rather than silently stale, which
  is enough for the first build.
