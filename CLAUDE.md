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
   tokenized: 20 custom properties on `:root`, and every literal color sits in the three `:root`
   blocks. The Google Fonts `<link>` is the one permitted external request, and the page has to be
   correct when it fails.

   `DESIGN.md` is the visual contract and `PRODUCT.md` the product record. Read `DESIGN.md` before
   changing anything visual; the MAP's 010 entry says what it replaced and why.
4. **Generated files never ship.** `data/*.json` and `index.html` are gitignored. The one exception
   is `data/overrides.json`, which is hand written, not regenerable, and tracked on purpose.

## Layout

```
scan.py               # scanner, page builder and categorize prompt, one file
index.template.html   # the page: inline CSS, inline JS, __SNAPSHOT_JSON__ placeholder
index.html            # generated
test_scan.py          # unittest, stdlib only; live counts skip on other machines
data/                 # generated, except overrides.json
docs/                 # MAP.md, tickets/, architecture review
```

`python3 scan.py --categorize` writes `data/categorize.md`, the prompt for the judgment calls the
scanner cannot make: domain, kind, gloss, the orchestration class, the health verdict and the
reach verdict. Paste it into an assistant, which writes `data/sidecar.json`, then scan again. It
emits only what the sidecar has not already answered, and writes nothing when every pool is empty.
Read ticket 013 before changing the prompt.

Splitting `scan.py` into a package was considered and deferred. It earns itself when the
`public.json` publish command from ticket 007 exists and gives the shared code a second consumer.
Until then it stays one file, because distribution is "copy two files".

## Things that will bite you

**Sidecar values must not contradict scanner values.** Kind and `orchestration_class` make the
same claim about the same skill and the panel prints them four lines apart, so
`kind == "Orchestrator"` and `orchestration_class == "orchestrator"` have to agree.
`test_kind_never_contradicts_the_adjudication` is the guard. Anything else the pass writes lands
next to a measured field: read what the page already says before adding a judgment beside it.

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
it stops working after the first filter. `wirePanel()` is the third site: `openPanel()` rebuilds the
panel with `innerHTML` on every open, so anything inside it binds there or not at all.

**The facet controls are never re-rendered.** Anything that changes `F` without a user gesture on
the control itself has to call `syncFacets()` to put the DOM back in step. Clear and Escape do.

**There are two empty states and they are not interchangeable.** `empty()` means the filters
matched nothing and offers a reset. `firstRun()` means the scan returned nothing, so it names the
roots and prints `scan_errors` instead, and it is the only reader of that field in the payload.
`colophon()` and `thesis()` return early on an empty library for the same reason: a paragraph of
zeros reads as a finding. Test this by running the scanner with `HOME` pointed at an empty
directory — it is a teammate's first screen and the easiest thing in the repo to break silently.

## Verifying a scanner change

```bash
python3 test_scan.py        # 74 tests, standard library unittest, no new dependency
```

Two kinds of test, and the split matters. The `Invariant*` classes build fixtures in a temp
directory and pin the rules the tickets decided — the one-level glob, the exclusion prefixes, the
id shape, the frontmatter repair, 006 Q12's reference guards, 002's three usage states,
`prune()` keeping zero. They pass on any machine. `LiveLibrary` pins the counts the tickets
assert (426 / 167 / 257 / 2, parse statuses, 22 candidates, 27 duplicate groups) and **skips
itself** unless `data/skills.json` exists and matches that library, because those numbers describe
one person's `~/.claude` and a teammate would otherwise get a red suite on a correct scan.
`LiveCategorized` is the same idea one level in and skips unless `data/sidecar.json` is present
too, because that file is gitignored and deleting it must not turn a correct scan red.

When a heuristic change moves a live number, that is the signal. Fix the code, or change the
number and amend the ticket that explains it. Do not change the number alone.

## Verifying a UI change

There are no tests for the page. `agent-browser` is available and drives a real browser against
`file://$PWD/index.html`. One caveat learned the hard way: `agent-browser click` does not reliably
land on the `all: unset` text buttons (`.js-reset`, `.js-insights`). Focus them and press Enter
instead, or you will chase a bug that is not there.

Worth checking after any render change: search keeps focus and caret, facet change updates the
count, Clear resets both the controls and the rows, mode toggle, column sort, panel open and close,
and `agent-browser errors` clean.

One trap when checking a specific entry: `agent-browser click '[data-id="x"]'` fails when the band
strip is on a band that row is not in. The search box narrows within the selected band, it does not
jump bands. This looks exactly like a broken selector.

## Highest value thing to add

**Reach tier two.** `scan.py --categorize` emits 85 entries in section 4 and nobody has answered
them, so `reach_verdict` is null on all 426 and the panel says "Pattern matches in the file, not a
verdict" for every flagged entry. It is the one section that needs 85 files opened, which is why
it was skipped, and it is the last unrun piece of ticket 013.

`test_scan.py` and the categorize pass were the previous entries here and both now exist.
