# 011 — Finding the same skill twice, and saying which copy to keep

Parent: `../MAP.md`
Label: `wayfinder:research`
Blocked by: 004 (entry identity), 005 (snapshot schema)
Status: closed 2026-08-19

## Question

The library has 426 rows and some of them are the same skill. Photos-style: group the copies, show
them side by side, recommend one. Three things had to be settled.

1. Which signals define a group?
2. How is the recommendation ranked, and what happens when nothing separates two copies?
3. What is the user allowed to do about it from inside the tool?

## Measurement

Live snapshot, 426 entries.

- Grouping on the id with any plugin prefix stripped: **27 groups covering 54 entries**.
- Byte-identical bodies anywhere in the library: **12 groups, 24 entries** — every one of them
  already inside a same-name group.
- Identical body under a *different* name: **0**.
- Cause: **25 of 27 groups** are `vercel@claude-plugins-official` against
  `vercel-plugin@vercel-vercel-plugin`, both enabled. The other two are a global skill of Eli's
  shadowed by a plugin copy: `agent-browser` and `skill-creator`.

## Resolution

### 1. Name matching only. Fuzzy similarity is not built.

The measurement above is the argument: cross-name similarity found nothing that name matching
missed, so `difflib` over 426 bodies would be cost with no yield. The door is left open — the
grouping function is one pass and a second signal drops in beside it — but it is not built on
speculation.

### 2. The recommendation ranks on snapshot evidence and names the one criterion that decided it.

Order: recorded uses, then recency, then yours over a plugin's, then defects, then whether the
frontmatter parses, then bundled resources, then body length. Ties fall through to the id so the
answer does not change between scans.

The page prints the deciding criterion, not the whole ladder: *Keep `agent-browser` — it is yours,
not a plugin's.* When every criterion ties, and 12 groups do because the files are byte-identical,
it says **"Nothing on record separates these copies"** and recommends neither. Picking one anyway
would be inventing a reason.

**A caveat the ranking inherits.** Twin copies usually show the *same* use count, because hook
injections drop the plugin prefix (002, and the `attribution: ambiguous` field in 005). The record
names the skill, not which installation of it ran. So usage rarely decides a plugin twin, and the
page says why rather than letting the number look decisive.

### 3. The tool recommends and hands over a path. It never deletes.

Decision 1 of the MAP is read-only with respect to a `SKILL.md`, and a page loaded from `file://`
has no write channel regardless. Both facts point the same way, and the second is why a delete
button could not be built even if the first were reversed.

**Deletion would also be the wrong fix for 25 of the 27 groups.** Both files belong to enabled
plugins, and the next plugin update restores whatever was removed. The real fix is one line in
`~/.claude/settings.json` disabling one plugin. A delete button would have been a button that
appears to work and quietly does nothing.

So the Resolve dialog names the cause, shows both paths, and copies the exact text to run:
the plugin key and the `enabledPlugins` line for a plugin twin, `rm -rf <dir>` only when the copy
being dropped is Eli's own. On today's data that destructive branch never renders — the dropped
copy is a plugin's in both mixed groups — and that is correct rather than a gap.

The `rm` button asks twice. The first click arms it and states what running the line does; the
second copies. Copying is not itself destructive, but the line it puts on the clipboard is one
paste away from being so.

## What shipped

- `attach_duplicates()` in `scan.py`, a `duplicates` array in the snapshot, `twin_group` on every
  entry, `counts.duplicate_groups`.
- A fourth rail destination, `Duplicates`, listing every group with its copies side by side.
- A `Twin` row in the entry panel.
- A native `<dialog>` Resolve modal. Native because `file://` blocks module loading, not the
  platform: Escape, focus trapping and the backdrop come free, and no dependency is added.
- Clipboard writes fall back to `execCommand` and then to a `user-select: all` block, because
  `navigator.clipboard` is not reliable on a `file://` origin.

## Left open

- Whether the two Vercel plugins should both stay enabled at all. Neither is a superset: the
  official plugin carries 5 skills the other lacks, the other carries 14, and the official one is
  four months newer. That is a decision about Eli's setup, not about Wayfinder.
