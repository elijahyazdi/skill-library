# Wayfinder

A browsable, filterable view of every skill this machine can reach.

Wayfinder scans `~/.claude` and answers four questions: what skills do I have, which have I
forgotten, which are worth sharing, and which need work. It is read-only. It never writes to a
`SKILL.md`.

## Quick start

```bash
python3 scan.py --prototype   # writes data/skills.json and builds index.html
open index.html
```

Needs Python 3 and PyYAML. Nothing else. No `npm install`, no bundler, no server.

`scan.py` without `--prototype` writes the snapshot only and leaves the page alone.

## How it works

Three files, merged in order:

| File | Written by | Tracked |
| --- | --- | --- |
| `data/skills.json` | `scan.py`, every run | no |
| `data/sidecar.json` | one batched LLM pass: domain, kind, orchestration verdict | no |
| `data/overrides.json` | you, by hand, and it wins | yes |

All three key on the entry `id`. `index.template.html` is the source for the page; `scan.py`
inlines the snapshot into it and writes `index.html`. Both generated JSON and the built page are
gitignored, because they carry your personal usage record.

## What it reads

- its own git tags and log, for the History timeline
- `~/.claude/skills`, one level deep
- enabled plugins, resolved from `installed_plugins.json` gated on `enabledPlugins`
- `~/.claude/commands`, for the delegation graph only, not as rows
- `~/.agents/.skill-lock.json`, for real per-skill timestamps and upstream owners
- `~/.claude/history.jsonl`, the primary usage signal, and transcripts as a secondary one

Every input is optional. A missing root is skipped, not an error.

## Reading the results

Three usage states, and the difference matters:

- **in use**: there is a record of it being invoked.
- **never used**: a full 167 day history exists and shows nothing.
- **no record**: only the 30 day transcript window was available, so absence proves nothing.

Two invocation paths leave no trace on disk at all. A blank record is the absence of evidence,
not evidence of absence. Domain and kind are inferred, not read off disk, and the page says so.

## Known gaps

- **No tests.** The scanner's numbers are asserted in the tickets and enforced by nothing.
- **Roughly 14 built-in skills are invisible.** They ship inside the harness, not on disk.
- **`REPO_ROOT` is hardcoded** to `~/Development/claude-skills`. It is skipped when absent, so the
  scan still runs elsewhere, but a teammate's own repo will not be picked up.
- **Publishing is specified and not built.** See ticket 007.
- **History is Wayfinder's own, not each skill's.** It reads this repo's annotated tags. No
  per-skill version history exists on the machine to show. See the MAP's open questions.

## Decisions

Every design decision lives in `docs/MAP.md` and the eight tickets under `docs/tickets/`. Read the
MAP before changing behavior. It records what was measured, what was rejected, and why.
