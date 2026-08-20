# 010 — What "risk" means when almost nothing declares a permission

Parent: `../MAP.md`
Label: `wayfinder:research`
Blocked by: 005 (needed the snapshot schema), 009 (reuses its two-tier pattern)
Status: closed 2026-08-19, tier one built, tier two deliberately deferred

## Question

The roadmap asked for a risk assessment: "the permissions a skill will ask for, so no skill is a
security or data risk". Before building it, three things had to be settled.

1. Is the unit a *declared permission* or *instructed behaviour*?
2. Which signals are precise enough to state as fact, and which need adjudication?
3. Does this cover Eli's 169, or all 426?

## Measurement

All 426 `SKILL.md` files in the live snapshot, read and matched with deliberately crude regexes.

| Signal | Entries |
|--------|---------|
| Declares `allowed-tools` in frontmatter | 2 |
| Body contains `curl` or `wget` | 22 |
| Body contains `rm -rf` | 1 |
| Body mentions `API_KEY`, `SECRET`, `TOKEN` or `credential` | 166 |
| Body contains a `POST`/`PUT`/`DELETE` to an http URL | 2 |

Across the wider `~/.claude` tree, including plugin skills the scanner does not index, the same
patterns hit 19, 61, 15 and 525.

## Resolution

### 1. The unit is instructed behaviour. The permission model does not exist.

Two entries of 426 declare `allowed-tools`. A feature built on "what permissions does this skill
request" would have nothing to show on 424 rows and would imply the other 424 request nothing,
which is the opposite of true: a skill's real capability is whatever the agent running it is
allowed to do, and the file says nothing about that.

So the flags describe **what the body tells an agent to do**, which is the only thing on disk.

### 2. Seven checks, all stated as text matches, never as verdicts.

`declares_tools`, `destructive`, `network`, `credential_paths`, `mcp_server`, `claude_home` from
regex over frontmatter plus body; `bundles_scripts` from a `scripts/` directory holding an
executable file. Measured on the live snapshot: 111 of 426 entries carry at least one, and the
per-flag counts are `credential_paths` 43, `mcp_server` 33, `network` 29, `bundles_scripts` 27,
`claude_home` 5, `destructive` 3, `declares_tools` 2.

Every label says "contains" or "names". `rm -rf` inside a fenced example and `rm -rf` in a step
the agent will run are identical to a regex, and the panel says so in a line under the list.

**No score.** A "risk: 7/10" next to a measured usage count would borrow that count's credibility
for a number nothing on disk supports. `PRODUCT.md` forbids fabricating a number, and a score is
the most fabricatable number available.

### 3. The 166-entry secret-word match was cut, and that is the whole argument for tier two.

`TOKEN` matches "token budget" and "tokenizer" in a library about LLM tooling. A flag firing on
39% of the rows is decoration. The replacement matches credential *paths* — `~/.ssh`, `~/.aws`,
`id_rsa`, `credentials.json`, keychain, a bare `.env` — and fires on 43.

Deciding what a match *means* is tier two, the same batched adjudication 003 and 009 use. It is
**not built**, for a reason that is about distribution rather than effort: `scan.py` has no API
client, the adjudication would be written into `data/sidecar.json`, and that file is gitignored.
A verdict that exists only on this machine is not part of the tool.

### 4. All 426, plugin skills included.

009 excludes plugin skills from health flags, because improving them is out of scope and 257 rows
of an unfixable to-do list is noise. Reach is different: the action on a flagged plugin skill is
"stop using it", which is available. It is also the population Eli reads least — 82 of the 100
first-pass flags were plugin rows — so excluding them would drop the finding exactly where it is
most useful.

### 5. Only four flags mark a row.

`destructive`, `network`, `credential_paths` and `mcp_server` mean the skill can act outside the
file it lives in, and those four raise an `acts outside` badge and answer the Reach facet. The
other three are context once the panel is open, not a reason to mark a row.

## What shipped

- `attach_reach()` in `scan.py`, `reach_flags` on every entry, `counts.reaching` in the snapshot.
- A `Reach` facet: Any / Acts outside the file / Touches nothing.
- An `acts outside` badge on cards and in the panel header.
- A `Reach` block in the entry panel listing every match in plain language, with the line that
  says these are pattern matches and not a verdict.

## Left open

- Tier two adjudication, above.
- Whether a `data/reach-overrides.json` should exist so a known-fine match can be silenced. Not
  built: 111 rows is readable, and a silencing file is a way to hide a real finding by habit.
