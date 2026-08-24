# 004 — What is a library entry, and where does its metadata come from

Parent: `../MAP.md`
Label: `wayfinder:research` (AFK)
Blocked by: none
Status: CLOSED 2026-08-18

## Question

Define the unique key for a library entry and the provenance rule for every displayed field.

The population is messier than it looks:

- 172 directories in `~/.claude/skills`.
- 1190 `SKILL.md` under `~/.claude/plugins`, spread across marketplaces: `caveman` 11,
  `claude-plugins-official` 31, `designer-skills` 91, `paper` 2, `pm-skills` 55, `ponytail` 12,
  and 988 with no marketplace segment in the path.
- `~/Development/claude-skills` is a separate git repo holding a *subset* of the 172, so some
  skills exist in two places with two possible histories.
- Name collisions are already visible in the available-skills list: `agent-browser` appears both
  standalone and as `vercel-plugin:agent-browser`; `nextjs` as both `vercel:nextjs` and
  `vercel-plugin:nextjs`; `skill-creator` twice.
- Several `-workspace` suffixed directories exist (`daily-reflection-workspace`,
  `design-accelerator-workspace`, `creator-content-workspace`, `discovery-sprint-workspace`).
  These are probably not library entries at all.

Research must establish:

1. The unique key. Path? `plugin:name`? Bare name is confirmed non-unique.
2. How `source` is derived for the facet: global / plugin / repo. Include what to do with the
   988 plugin skills whose path has no marketplace segment.
3. Whether the same skill present in both `~/.claude/skills` and `~/Development/claude-skills`
   is one entry or two, and which copy is authoritative.
4. How `author` is inferred when only 3 of 172 declare it. Candidates: marketplace owner for
   plugin skills, git author, "Eli" by default for the personal set, or leave unknown.
5. Whether `-workspace` dirs, and any dir without a `SKILL.md`, are excluded.
6. Whether frontmatter parsing needs a YAML library or a regex is enough. Note that at least one
   description is a quoted multi-line string, so naive line parsing will break.

Report the entry schema fields and the provenance rule for each.

## Resolution

Status: resolved 2026-08-18. All six questions answered against disk.

### What the population actually is

The three headline numbers in the Question section are directory counts, not entry counts. Measured
breakdown:

- `~/.claude/skills` holds 173 directories. One is `.git`, five are `-workspace` eval output, so
  167 have a top-level `SKILL.md`. 84 of the 167 are symlinks into `~/.agents/skills/`, which is a
  skill-manager install root with a lockfile at `~/.agents/.skill-lock.json`.
- The 988 plugin `SKILL.md` files "with no marketplace segment" are all under
  `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`. They do carry a marketplace name, it
  just sits at path position 2 instead of under `marketplaces/`. The reason there are so many is
  that the cache retains every previously installed version: five PostHog versions, two Vercel
  versions, three Superpowers versions, five Figma versions and so on. Only the version named in
  `installed_plugins.json` is live. 678 of the 988 are stale duplicates.
- The 202 under `~/.claude/plugins/marketplaces/` are marketplace source checkouts, not
  installations. Only three of the six marketplaces there have an installed plugin
  (`caveman`, `paper`, `designer-skills/visual-critique`). The 91 `designer-skills`, 55 `pm-skills`
  and 12 `ponytail` skills are catalog contents for plugins that were never installed and are not
  enabled in `settings.json`.
- 33 more are vendored `upstream/SKILL.md` copies nested inside Vercel plugin skill directories.
- `~/Development/claude-skills` is not a separate project. It is the same git repository as
  `~/.claude/skills` (identical `origin`, `https://github.com/elijahyazdi/claude-skills.git`, shared
  init commit `4e9e78a`). It holds 42 skills plus `index.html` and a generated `skills.json`, which
  is prior art for this effort.

After exclusions the real library is **428 entries**: 167 global, 259 from the 13 enabled plugins,
and 2 that exist only in the repo (`algorithmic-art`, `reflect`).

### 1. The unique key

Bare name is not unique. Across global, repo and plugin populations there are **96 colliding names
covering 206 candidate files**. The collisions fall into four kinds:

- **Global versus repo**, 40 names. Every skill in `~/Development/claude-skills` except
  `algorithmic-art` and `reflect` also exists in `~/.claude/skills`.
- **Same skill shipped by two different plugins**, 24 names. `vercel@claude-plugins-official` and
  `vercel-plugin@vercel-vercel-plugin` both ship `nextjs`, `ai-sdk`, `ai-gateway`, `auth`,
  `bootstrap`, `chat-sdk`, `deployments-cicd`, `env-vars`, `knowledge-update`, `marketplace`,
  `next-cache-components`, `next-forge`, `next-upgrade`, `react-best-practices`,
  `routing-middleware`, `runtime-cache`, `shadcn`, `turbopack`, `vercel-agent`, `vercel-cli`,
  `vercel-functions`, `vercel-sandbox`, `vercel-storage`, `verification`, `workflow`, plus the
  plugin-internal `benchmark-*`, `plugin-audit`, `release` and `vercel-plugin-eval`.
- **Three-way and four-way**, the worst cases. `skill-creator` appears four times (global, repo,
  the installed `skill-creator@claude-plugins-official`, and the marketplace checkout).
  `agent-browser` appears three times (global, repo, `vercel-plugin`). `frontend-design` three
  times (global, repo, marketplace checkout). `cavecrew`, `caveman`, `caveman-compress` and
  `caveman-stats` each appear four times because the caveman repo publishes its skills at both the
  repo root and under `plugins/caveman/`.
- **Cross-marketplace**, e.g. `jobs-to-be-done` in both `designer-skills` and `pm-skills`;
  `access` and `configure` each three times across the Discord, Telegram and iMessage external
  plugins in the official catalog.

Frontmatter `name` is also not a safe key. It disagrees with the directory name on 8 entries
(`kaparthy-guidelines` on disk declares `karpathy-guidelines`; the six `sanity-*` directories drop
the `sanity-` prefix in their frontmatter), and two entries have no parseable `name` at all
(`~/.claude/skills/style-tiles` has no frontmatter block, and `~/Development/claude-skills/ux-flow`
has none either).

**Decision.** The unique key is the absolute path to the skill directory. It is the only value that
is unique by construction and it is what the UI needs anyway to hand Eli a file path. A second
field, `id`, carries the human-readable qualified name and is what the UI displays and links:
`<name>` for global entries, `<plugin>:<name>` for plugin entries, `repo:<name>` for repo-only
entries. `id` is unique across the canonical 428 after the dedup rules below. Bare `name` is kept
as a separate searchable field but is never used as a key.

### 2. Deriving `source`

`source` is a three-value facet derived from which scan root the file was found under, and the roots
are enumerated rather than globbed:

- `global` for anything directly under `~/.claude/skills/<name>/SKILL.md`.
- `plugin` for anything under an `installPath` listed in
  `~/.claude/plugins/installed_plugins.json` whose plugin id is also `true` in the `enabledPlugins`
  block of `~/.claude/settings.json`. Those two lists agree exactly today, 13 plugins.
- `repo` for anything under `~/Development/claude-skills/<name>/SKILL.md`.

**The rule for the 988.** Do not walk `~/.claude/plugins` at all. Walk each live `installPath`
instead. That single change resolves the 988 without any path parsing: 678 stale cache files fall
out because they belong to versions no longer installed, and the 202 marketplace checkouts fall out
because a marketplace checkout is a catalog, not an installation. What remains is 259 entries after
also dropping `upstream/`, plugin-internal `.claude/skills/`, and caveman's duplicate
`plugins/caveman/skills/` tree.

Two derived fields come free from the same source: `plugin` (the `name@marketplace` id) and
`marketplace` (the segment after `@`). Both are null for `global` and `repo`.

The 91 `designer-skills`, 55 `pm-skills` and 12 `ponytail` marketplace skills are deliberately not
indexed. They are installable, not installed, and a library of what Eli has should not show what he
has not installed. If an "available to install" view is ever wanted it is a different surface with a
different data source, namely `plugin-catalog-cache.json` and the `marketplace.json` files.

### 3. Global versus repo: one entry or two

One entry, with global authoritative.

The two trees are the same repository. `~/.claude/skills` is the working copy that Claude Code
actually loads; `~/Development/claude-skills` is a stale published mirror that also holds the
generated `index.html` and `skills.json`. `~/.claude/skills` has a dirty tree with 149 untracked
paths, which is the accumulation of every skill added since the single init commit.

Diffing all 40 overlapping pairs: 26 trees are byte-identical, 14 differ, and 8 of those differ in
`SKILL.md` itself. Every content difference runs the same direction, with the global copy newer and
longer:

- `bug-detective` 184 lines in repo, 211 global (global adds a "Phase 0, Build a Feedback Loop"
  section).
- `design-accelerator` 101 versus 203 (global replaces a generic pattern list with a
  reference-backed polish method, and adds `evals/` and `references/`).
- `morning` 192 versus 227 (global adds a field-intelligence step).
- `weekly` 125 versus 129 (global corrects the notes vault root, path redacted, and reads the
  newer `/daily-reflection` output).
- `review` 84 versus 96 (global switched output from JSON to a plain-text report).
- `data-modeling`, `ux-flow`, `grill-me` likewise updated in global. The repo `ux-flow` has lost its
  frontmatter entirely, which the global copy still has.

**Decision.** Deduplicate on bare name, preferring `global`. The repo copy is not shown as a
separate entry; instead the merged entry carries `also_in_repo: true` and `repo_differs: true|false`
so the library can surface the 14 drifted pairs as a maintenance signal. The two repo-only skills
(`algorithmic-art`, `reflect`) are indexed with `source: repo`. Nothing in the repo overrides
anything in global.

### 4. Deriving `author`

Only 3 of 167 global skills declare `metadata.author`: `fact-checker` (`awesome-llm-apps`),
`sanity-portable-text-conversion` and `sanity-portable-text-serialization` (both `sanity`). Git is
no help. `~/.claude/skills` has one commit and `~/Development/claude-skills` four, all authored by
`Elijah Yazdi <hi@elijahyazdi.com>` plus one `github-actions[bot]`, so per-file git authorship
carries zero discriminating information and is not worth reading.

What is actually available, per population:

- **Plugin entries, 259 of 259 minus one.** Every live plugin has a `plugin.json` with an
  `author.name`, and often a `repository` URL: Figma, Vercel, Vercel Labs, Sentry, Supabase,
  PostHog, Paper, Anthropic, `Jesse Vincent <jesse@fsck.com>` for superpowers,
  `Julius Brussee` for caveman, `MC Dean` for visual-critique. Only `swift-lsp` lacks one, and it
  ships no skills. Each marketplace also has a `marketplace.json` with `owner.name` and sometimes
  `owner.email` or `owner.url`, which is the fallback when `plugin.json` has no author.
- **Global entries, 84 of 167.** `~/.agents/.skill-lock.json` is the find that closes this
  question. It has one record per symlinked skill with `source` (a GitHub `owner/repo`),
  `sourceType`, `sourceUrl`, `skillPath`, `skillFolderHash`, `installedAt` and `updatedAt`. The
  owners are `coreyhaines31/marketingskills` (49), `mattpocock/skills` (34) and
  `remotion-dev/skills` (1). The 84 lock records map exactly onto the 84 symlinks.
- **The remaining 83 global entries and 2 repo-only entries.** No metadata anywhere. These are the
  real directories Eli wrote or hand-copied.

**Decision, in precedence order.** `metadata.author` from frontmatter if declared. Otherwise for
plugin entries, `plugin.json` `author.name`, falling back to `marketplace.json` `owner.name`.
Otherwise for global entries with a lockfile record, the `source` owner from
`~/.agents/.skill-lock.json`, rendered as the GitHub owner with `sourceUrl` as the link. Otherwise
`"Eli"`. Defaulting to Eli for the residual 85 is defensible rather than fabricated: they are
untracked directories in his own home skills root with no upstream provenance of any kind, which is
exactly what "he wrote it or he adopted it as his own" looks like on disk. The entry also carries
`author_source` with one of `frontmatter | plugin | marketplace | skill-lock | assumed` so the UI can
mark the assumed ones and locked decision 5 in the map is not violated. `~/.agents/.skill-lock.json`
also supplies a genuine `updatedAt` per skill for those 84, which is the only real per-skill
timestamp on the machine and should be used where present.

### 5. Exclusions

Confirmed by inspection, all excluded:

- The five `-workspace` directories in `~/.claude/skills` (`creator-content-workspace`,
  `daily-reflection-workspace`, `design-accelerator-workspace`, `discovery-sprint-workspace`,
  `project-plan-builder-workspace`) and the two in the repo. They contain
  `iteration-N/eval-*/`, `benchmark.json`, `feedback.json`, `vault-fixture/` and `grade.py`. They
  are `/skill-creator` eval output. The exclusion must be a path-prefix exclusion, not just "no
  top-level SKILL.md", because `design-accelerator-workspace/skill-snapshot-old/SKILL.md` is a real
  nested `SKILL.md` and would otherwise be indexed as an entry.
- `.git`, and `.DS_Store` files, which are present in most of these directories.
- Stale plugin cache versions, 678 files, handled by the enumerate-installPath rule in question 2.
- Marketplace checkouts of uninstalled plugins, 202 files, same rule.
- `upstream/SKILL.md`, 33 files. These are vendored source copies inside a plugin's own skill
  directories (`vercel/0.45.1/skills/nextjs/upstream/SKILL.md` and similar). They are not separate
  skills and their bare name always collides with the parent.
- Plugin-internal `.claude/skills/` trees, 21 files across the two Vercel plugin installs
  (`benchmark-agents`, `benchmark-e2e`, `benchmark-sandbox`, `benchmark-testing`, `plugin-audit`,
  `release`, `vercel-plugin-eval`). These are the plugin repo's own development skills, not skills
  the plugin exposes to Eli, and none appear in Claude Code's available-skills list.
- Caveman's duplicate `plugins/caveman/skills/` tree, 4 files, which restates the skills already at
  the install root.

Note that `skill-creator` is **not** excluded. Despite the `-workspace` directories being its eval
output, `~/.claude/skills/skill-creator/SKILL.md` exists and is a real skill. It does collide with
`skill-creator@claude-plugins-official`, which the qualified `id` in question 1 resolves.

One residual fog, not this ticket's problem: Claude Code also surfaces built-in skills that exist in
none of these roots (`design`, `dataviz`, `artifact-design`, `artifact-capabilities`,
`artifact-diagramming`, `update-config`, `loop`, `schedule`, `run`, `init`, `security-review`,
`keybindings-help`, `simplify`, `fewer-permission-prompts`). They are not on disk and cannot be
indexed by a filesystem scan.

### 6. Frontmatter parsing

`python3` on this machine is 3.9.6 and **PyYAML 6.0.3 is available**, so no dependency needs to be
added.

Empirical test over all 1,399 `SKILL.md` files reachable from the three roots, comparing a naive
line regex against `yaml.safe_load`:

- **Naive regex fails outright on 2 files**, both the missing-frontmatter cases (`style-tiles`,
  repo `ux-flow`). That looks like a win for regex until you check the values.
- **Naive regex silently returns the wrong `description` on 606 files.** These are block scalars.
  `humanizer` and `fact-checker` use `description: |`, and `brand-workshop`, `bug-detective`,
  `council`, `project-estimate` and `remotion-app-video` use `description: >`, so the regex captures
  the empty string or the sigil instead of the text. Hundreds of PostHog and Figma plugin skills do
  the same. A library whose primary displayed field is the description cannot ship a parser that
  gets 43 percent of them wrong, and the failure is silent rather than loud, which is worse.
- **`yaml.safe_load` fails on 24 files, of which 16 are in the global 167.** Twenty-one are
  `ScannerError: mapping values are not allowed here`, caused by an unquoted `: ` inside a plain
  scalar description (`career-strategy`, `intentional-buy`, `meeting-agenda`, `feature-sprint`,
  `wireframe-ready`, `to-issues`, `marketing-sprint`, `design-accelerator`, `to-prd`, and their repo
  twins). One is `ScannerError: found character '@'` in `vercel-plugin/skills/next-forge`, whose
  description contains a bare `@repo`. Two are the no-frontmatter files.

**Decision.** Use PyYAML with a repair fallback. Parse the block between the leading `---` fences
with `yaml.safe_load`. On exception, re-emit every single-line top-level `key: value` pair with the
value force-quoted, leaving block scalars and already-quoted values alone, and parse again. Measured
result: 1,375 clean, 21 recovered by repair, 3 unrecoverable. For the unrecoverable three, fall back
to the directory name for `name`, a regex-extracted first line for `description`, and set
`parse_status: fallback` on the entry so the library shows them as needing attention. Do not attempt
to fix the source files; the tool is read-only.

`parse_status` therefore takes one of `ok | repaired | fallback`, and doubles as the first concrete
input to the "needs refinement" signal the map lists as unspecified.

### Entry schema and provenance

One entry per skill. Field, then where the value comes from.

| Field | Provenance |
| --- | --- |
| `path` | Absolute path to the skill directory. The unique key. Filesystem. |
| `skill_file` | `path + "/SKILL.md"`. Filesystem. |
| `id` | Display and link key. `<name>` for global, `<plugin>:<name>` for plugin, `repo:<name>` for repo-only. Derived. |
| `name` | Directory basename, always. Frontmatter `name` is recorded separately because it disagrees on 8 entries and is absent on 2. |
| `declared_name` | Frontmatter `name` when present and different from `name`, else null. Diagnostic only. |
| `description` | Frontmatter `description` via PyYAML with the repair fallback. Regex-extracted first line for the 3 unrecoverable files. Never truncated at parse time. |
| `source` | `global` / `plugin` / `repo`, from which enumerated scan root produced the file. |
| `plugin` | `name@marketplace` from `installed_plugins.json`, null for global and repo. |
| `marketplace` | Segment after `@` in `plugin`, null otherwise. |
| `plugin_version` | `version` from the plugin's `installed_plugins.json` record, null otherwise. |
| `version` | Frontmatter `metadata.version` (51 of 167) or top-level `version` (3), else `plugin_version` for plugin entries, else `"unknown"`. |
| `author` | Precedence: frontmatter `metadata.author`, then `plugin.json` `author.name`, then `marketplace.json` `owner.name`, then `~/.agents/.skill-lock.json` `source` owner, then `"Eli"`. |
| `author_source` | `frontmatter` / `plugin` / `marketplace` / `skill-lock` / `assumed`. Lets the UI mark assumed values. |
| `upstream_url` | `sourceUrl` from `.skill-lock.json`, or `repository` from `plugin.json`, else null. |
| `updated_at` | `updatedAt` from `.skill-lock.json` for the 84 symlinked global skills; `lastUpdated` from `installed_plugins.json` for plugin entries; else `"unknown"`. File mtimes are bulk-copy stamps and are never used. |
| `is_symlink` | True for the 84 global entries that resolve into `~/.agents/skills/`. Filesystem. |
| `also_in_repo` | True when a same-named directory exists in `~/Development/claude-skills`. |
| `repo_differs` | True when the two `SKILL.md` files differ. True for 8 of the 40 overlaps today. |
| `model_invocable` | False when frontmatter sets `disable-model-invocation: true` (22 of 167), else true. |
| `parse_status` | `ok` / `repaired` / `fallback`. |
| `body_lines` | Line count of the file. Cheap size signal for the later "needs refinement" work. |
| `has_resources` | True when the directory contains any of `references/`, `scripts/`, `agents/`, `assets/`, `evals/`. Filesystem. |
| `category` | Not in this schema. It comes from the sidecar file per locked decision 4 in the map, joined on `id`. |
| `times_used`, `last_used` | Not in this schema. Mined from `~/.claude/projects/*/*.jsonl`, joined on `name`. Separate ticket. |

### Consequences for other tickets

- The snapshot is roughly 428 entries, not 1,362. Any UI ticket sizing itself on 1,362 is sizing for
  a population that includes 678 stale cache duplicates.
- The scanner must read four side files, not just walk directories:
  `~/.claude/plugins/installed_plugins.json`, `~/.claude/plugins/known_marketplaces.json`,
  each live plugin's `plugin.json`, and `~/.agents/.skill-lock.json`.
- `~/Development/claude-skills/skills.json` and `index.html` already exist as a first pass at this
  problem, generated by `.github/workflows/build-skills.yml`. Its schema is
  `name, description, folder, path, slug, body` over 42 skills, with the full body inlined. Worth
  reading before writing the scanner, and worth deciding whether it gets retired or becomes the
  publish target.
- `pm-skills`' `marketplace.json` carries a `category` and a `tags` array per skill. If those 55 are
  ever indexed, category for them is free and does not need the LLM pass.
- On the map's open question about `~/.claude/commands`: there are 11 files, 9 with frontmatter. They
  are not skills, they have no directory, no resources and no usage records under the Skill tool, and
  none of the fields above except `name` and `description` would populate. Recommend leaving them
  out. Revisit only if Eli asks.
