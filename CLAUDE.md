# Wayfinder

Read-only indexer over `~/.claude`. Python scanner plus one static HTML page. See `README.md` for
what it does and `docs/MAP.md` for why it does it that way.

## Read the MAP before changing behavior

`docs/MAP.md` and `docs/tickets/001-008` are the decision record. They carry measured numbers and,
more usefully, the alternatives that were tried and rejected. Most "obvious improvements" to this
repo are already in there with a reason they were not taken. If you are about to reverse a
decision, amend the MAP in the same change so the record stays honest.

## Constraints that are not preferences

Violating any of these breaks the product, not just the style:

1. **Never write to a `SKILL.md`.** Read-only is decision 1. The tool hands over a path instead.
2. **No build step, no framework, no dependency beyond PyYAML.** `open index.html` has to work off
   the filesystem with no server.
3. **No ES modules, no external `<script src>` or `<link>` for app code.** `file://` blocks module
   loading. This is why the CSS and JS live inline in `index.template.html`, and why splitting them
   into `styles.css` or component files is a regression rather than a cleanup. The CSS is already
   tokenized: 17 custom properties on `:root`, and every literal color sits in the two `:root`
   blocks.
4. **Generated files never ship.** `data/*.json` and `index.html` are gitignored. The one exception
   is `data/overrides.json`, which is hand written, not regenerable, and tracked on purpose.

## Layout

```
scan.py               # scanner and page builder, one file
index.template.html   # the page: inline CSS, inline JS, __SNAPSHOT_JSON__ placeholder
index.html            # generated
data/                 # generated, except overrides.json
docs/                 # MAP.md, tickets/, architecture review
```

Splitting `scan.py` into a package was considered and deferred. It earns itself when the
`public.json` publish command from ticket 007 exists and gives the shared code a second consumer.
Until then it stays one file, because distribution is "copy two files".

## Things that will bite you

**The payload omits empty fields.** `prune()` in `scan.py` drops `None`, `False`, and empty
strings, lists and dicts before inlining, which is worth about 22% of page weight at 426 entries.
Zero is kept, because a usage count of 0 is the `never_used` finding and not an absence. The page
reads almost everything with a truthiness or null check; the three arrays it indexes into directly
are restored right after `JSON.parse`. If you add a field the page indexes into, add it there too.

**`render()` is boot only. Everything else calls `refresh()`.** `refresh()` replaces `#rows` and
updates the count, the mode buttons and the Clear button. Filtering used to rebuild the whole
shell, which destroyed the search box mid-keystroke and needed a hand-rolled focus and caret
restore. Do not reintroduce a full render on a filter change.

Listeners are split to match: `wireShell()` runs once at boot for everything that survives a
refresh, `wireRows()` runs after every refresh for what lives inside `#rows`. Putting a persistent
element's listener in `wireRows()` double-binds it. Putting a row's listener in `wireShell()` means
it stops working after the first filter.

**The facet controls are never re-rendered.** Anything that changes `F` without a user gesture on
the control itself has to call `syncFacets()` to put the DOM back in step. Clear and Escape do.

## Verifying a UI change

There are no tests. `agent-browser` is available and drives a real browser against
`file://$PWD/index.html`. One caveat learned the hard way: `agent-browser click` does not reliably
land on the `all: unset` text buttons (`.js-reset`, `.js-insights`). Focus them and press Enter
instead, or you will chase a bug that is not there.

Worth checking after any render change: search keeps focus and caret, facet change updates the
count, Clear resets both the controls and the rows, mode toggle, column sort, panel open and close,
and `agent-browser errors` clean.

## Highest value thing to add

A `test_scan.py` pinning the numbers the tickets already assert: 426 entries, 167 global, 257
plugin, 2 repo, parse status counts, and the orchestration candidate count. The scanner is 831
lines of heuristics whose correctness currently rests on nobody having broken it yet.
