# Skill Library

A browsable, filterable view of every skill this machine can reach.

Skill Library scans `~/.claude` and answers four questions: what skills do I have, which have I
forgotten, which are worth sharing, and which need work. It is read-only. It never writes to a
`SKILL.md`.

## Install

```bash
git clone https://github.com/elijahyazdi/skill-library.git skill-library
cd skill-library
python3 -m venv .venv && source .venv/bin/activate
pip install pyyaml             # the only dependency
python3 scan.py --prototype    # writes data/skills.json and builds index.html
open index.html
```

Python 3.9 or later and PyYAML. Nothing else. No `npm install`, no bundler, no server.

macOS Homebrew Python refuses a bare `pip3 install` (PEP 668, "externally-managed-environment").
The venv above sidesteps it without touching Homebrew's own packages. Re-run just
`source .venv/bin/activate` in future shells before using `scan.py`.

Everything the page needs is inlined into `index.html`, so it opens off the filesystem. The one
external request is the Google Fonts stylesheet, and the page is correct without it.

You can also copy `scan.py` and `index.template.html` into any directory and run them there.
`scan.py` creates its own `data/` next to itself. Nothing else in the repo is required at runtime.

## Running it

```bash
python3 scan.py               # snapshot only, leaves the page alone
python3 scan.py --prototype   # snapshot plus index.html
python3 scan.py --repo PATH   # also scan a skills checkout outside ~/.claude
python3 scan.py --categorize  # write the prompt for the judgment calls
python3 scan.py --help
```

## Filling in domain and kind

The scanner reads what is on disk. It cannot tell you a skill's domain, its kind, a one-line
gloss, whether it really orchestrates the skills it names, or what a `rm -rf` in its body is
actually doing. Those come from one pass you run yourself:

```bash
python3 scan.py --categorize   # writes data/categorize.md
```

Paste that file into Claude Code or any assistant. It writes `data/sidecar.json`. Scan again and
the Domain and Kind facets fill in and the Analysis view starts scoring. Re-running `--categorize`
emits only what the sidecar has not already answered, so adding four skills means a four-entry
prompt. It writes nothing when there is nothing left to ask.

No API key, no network, no account. The tool prepares the prompt and hands it over, which is the
same thing it does with a skill's path.

## Tests

```bash
python3 test_scan.py          # 74 tests, standard library, no test framework to install
```

57 of them pin rules and pass anywhere. The other 17 pin the counts this repo's tickets assert and
skip themselves unless `data/skills.json` came from the library those numbers describe, so a
correct scan on your machine never shows up as a failure.

## Keeping it current

There is no watcher and no hook. Rescan when you want to; the page states its own age and warns
at 14 days, then again at 30, because transcripts roll off at 30 and usage coverage degrades.

The snapshot and the built page carry your personal usage record. Both are gitignored. Do not
send `index.html` to anyone — send them this repo and let them run their own scan.

Nothing here writes to a `SKILL.md`, ever. Acting on a finding means copying the path the page
gives you and opening it somewhere else.

## How it works

Three files, merged in order:

| File | Written by | Tracked |
| --- | --- | --- |
| `data/skills.json` | `scan.py`, every run | no |
| `data/sidecar.json` | `scan.py --categorize`, then an assistant | no |
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

Opening a record shows what the file itself says, never a rewrite of it: the skill's own Step
headings as a workflow, its own `Example` section verbatim where it has one, and what the text
reaches for. Every action ends at the clipboard. A **Copy a revision prompt** button turns a note
into a paste for Claude Code, and a **Copy a fork prompt** button does the same for forking an
orchestrator, closure and all. Nothing on the page writes, moves, or creates a file.

## Known gaps

- **The reach verdicts are unanswered.** `--categorize` emits them as section 4, which needs
  every flagged file opened. Until someone does, the panel says "Pattern matches in the file, not
  a verdict" for all 111 flagged entries, which is true and is the point. See ticket 013.
- **The sidecar does not travel.** It is gitignored like every other generated file, so each
  person runs `--categorize` against their own library. That is the design, not an oversight.
- **The page has no tests.** `test_scan.py` covers the scanner. The HTML is verified by hand
  against a real browser; CLAUDE.md lists what to check.
- **Roughly 14 built-in skills are invisible.** They ship inside the harness, not on disk.
- **`--repo` defaults to `~/Development/claude-skills`,** which is one person's path. It is
  skipped when absent, so the scan runs fine elsewhere, but pass your own path to be indexed.
- **Publishing is specified and not built.** See ticket 007.
- **History is Skill Library's own, not each skill's.** It reads this repo's annotated tags. No
  per-skill version history exists on the machine to show. See the MAP's open questions.

## Decisions

Every design decision lives in `docs/MAP.md` and the fourteen tickets under `docs/tickets/`. Read the
MAP before changing behavior. It records what was measured, what was rejected, and why.
