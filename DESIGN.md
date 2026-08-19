---
name: Wayfinder
description: A records workspace for the skills on this machine, built at CRM density.
colors:
  canvas: "#FBFBFA"
  surface: "#FFFFFF"
  panel: "#F6F6F4"
  raise: "#F1F1EF"
  hairline: "#E9E9E6"
  edge: "#DCDCD8"
  ink: "#1A1A18"
  ink-2: "#5E5E59"
  ink-3: "#8B8B85"
  accent: "#3B5BDB"
  accent-wash: "#EEF1FD"
  accent-edge: "#C6D0F7"
  signal-cold: "#B0592C"
  signal-cold-wash: "#FBEFE8"
  signal-live: "#2F7D4F"
  signal-live-wash: "#EAF4EE"
  canvas-dark: "#171716"
  surface-dark: "#1E1E1C"
  panel-dark: "#1A1A19"
  raise-dark: "#262624"
  hairline-dark: "#2B2B28"
  edge-dark: "#3A3A36"
  ink-dark: "#EDEDEA"
  ink-2-dark: "#A3A39C"
  ink-3-dark: "#7A7A73"
  accent-dark: "#8DA2F5"
  accent-wash-dark: "#1E2233"
  accent-edge-dark: "#333B57"
  signal-cold-dark: "#DFA07A"
  signal-cold-wash-dark: "#2A211B"
  signal-live-dark: "#7FBF9A"
  signal-live-wash-dark: "#1B2620"
typography:
  display:
    fontFamily: "Schibsted Grotesk, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "24px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Schibsted Grotesk, ui-sans-serif, system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-0.012em"
  title:
    fontFamily: "Schibsted Grotesk, ui-sans-serif, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 550
    lineHeight: 1.4
    letterSpacing: "-0.006em"
  body:
    fontFamily: "Schibsted Grotesk, ui-sans-serif, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: "normal"
  label:
    fontFamily: "Schibsted Grotesk, ui-sans-serif, system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 550
    lineHeight: 1.2
    letterSpacing: "0.02em"
  data:
    fontFamily: "JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, monospace"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.4
    fontFeature: "tnum"
rounded:
  bar: "2px"
  xs: "4px"
  sm: "6px"
  md: "8px"
  lg: "10px"
  pill: "999px"
spacing:
  "1": "4px"
  "2": "8px"
  "3": "12px"
  "4": "16px"
  "5": "20px"
  "6": "24px"
  "8": "32px"
  "10": "40px"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.surface}"
    rounded: "{rounded.sm}"
    padding: "6px 12px"
    typography: "{typography.title}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "6px 12px"
    typography: "{typography.title}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.sm}"
    padding: "5px 8px"
    typography: "{typography.title}"
  chip:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.sm}"
    padding: "3px 8px"
    typography: "{typography.label}"
  chip-selected:
    backgroundColor: "{colors.accent-wash}"
    textColor: "{colors.accent}"
    rounded: "{rounded.sm}"
    padding: "3px 8px"
    typography: "{typography.label}"
  input-search:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "6px 10px 6px 30px"
    height: "30px"
    typography: "{typography.body}"
  record-row:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "0"
    height: "34px"
    padding: "0 10px"
  nav-item:
    backgroundColor: "transparent"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.sm}"
    padding: "5px 8px"
    typography: "{typography.title}"
  nav-item-active:
    backgroundColor: "{colors.raise}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "5px 8px"
    typography: "{typography.title}"
---

# Design System: Wayfinder

## Overview

**Creative North Star: "The Cold-Outreach CRM, for skills"**

Wayfinder is a records workspace. A skill is a record; the last time it ran is the last time it was
contacted; a skill with 167 days of silence is a cold account, not a table cell. The whole system
is borrowed from the CRM the audience already reads daily — the Attio register: a quiet workspace
chrome that stays out of the way, hairline-ruled rows at real density, and one small blue accent
that only ever means "current" or "selected". Nothing here is editorial. There is no serif, no
display face, no page that reads like an essay. It reads like a tool that expects to be used again
in ten minutes.

The register earns the product's actual job. Recall beats lookup here: the point of opening
Wayfinder is to be told about a skill you own and forgot. A CRM is the one interface family whose
native grammar is exactly that — pipeline bands, last-contact recency, a queue of accounts that
have gone quiet. So the bands are not a filter widget bolted onto a table; they are the spine, and
the table is the register underneath them.

Density is a feature, not a compromise. 34px rows, 13px text, tabular figures, hairlines instead of
cards. Whitespace is spent on the workspace edges and on the reading panel, never inside the
register. What the previous design got wrong is recorded as the anti-reference: mixed rhythms
between masthead, bench, analysis, and panel; a 34px serif headline sitting above 13px rows; and
raw radios and native selects standing in for a filter language.

**Key Characteristics:**

- One family (Schibsted Grotesk), one accent (workspace blue), two signal hues (cold, live).
- Hairlines and tonal layering carry structure. Shadows appear only when something floats.
- A 4px spatial grid, 34px record rows, 30px controls. Every control on a row is the same height.
- Tabular figures everywhere a number can change.
- Every state has a non-color carrier: a word, a dot with a distinct fill, or a border style.

## Colors

A warm-neutral workspace: paper-white surfaces on a faintly warm canvas, hairlines rather than
boxes, and one restrained blue that means current, selected, or focused and nothing else.

### Primary

- **Workspace Blue** (`{colors.accent}`): the current nav destination, the selected band, the
  selected row, focus rings, and links to a path. It never fills a large region and never
  decorates a heading.
- **Blue Wash** (`{colors.accent-wash}`) and **Blue Edge** (`{colors.accent-edge}`): the selected
  chip, the selected row, and the active band underline. The wash is the only tinted fill allowed
  behind text at row scale.

### Secondary

- **Cold Clay** (`{colors.signal-cold}`, wash `{colors.signal-cold-wash}`): the never-called state
  and the needs-work flag. This is the color of the product's core finding, so it appears more
  often than the accent in a default view. That is intended.
- **Live Green** (`{colors.signal-live}`, wash `{colors.signal-live-wash}`): the in-rotation state
  only. Never a success toast, never a generic positive.

### Neutral

- **Canvas** (`{colors.canvas}`): the app ground behind the register.
- **Surface** (`{colors.surface}`): rows on hover, the reading panel, inputs, cards.
- **Panel** (`{colors.panel}`) and **Raise** (`{colors.raise}`): the left workspace rail and the
  resting state of segmented controls and active nav items.
- **Hairline** (`{colors.hairline}`) for row dividers, **Edge** (`{colors.edge}`) for control
  borders and section rules.
- **Ink / Ink-2 / Ink-3** (`{colors.ink}`, `{colors.ink-2}`, `{colors.ink-3}`): record names and
  primary values / descriptions and secondary values / labels, units, and empty markers.

Dark mode is a real mode, not an inversion: near-black warm grays (`{colors.canvas-dark}` through
`{colors.edge-dark}`), lifted accent and signal hues, and the same tonal order.

### Named Rules

**The Three-Hue Rule.** Blue, clay, green. A fourth hue does not enter the system, including for
charts; the analysis grid bands with tint plus border style, not with a new color.

**The No-Data Rule.** Absent evidence renders as `{colors.ink-3}` and an em dash, never as a zero
and never in a signal hue. Zero uses is a finding and is drawn in clay; no record is a gap and is
drawn in gray.

## Typography

**UI Font:** Schibsted Grotesk (fallback `ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif`)
**Data Font:** JetBrains Mono (fallback `ui-monospace, SFMono-Regular, Menlo, monospace`)

**Character:** One neutral grotesque doing every job, tuned tight and small, with a monospace
reserved for things that are literally values: counts, days, line totals, and filesystem paths.
The pairing has no voice of its own on purpose. The data is the voice.

### Hierarchy

- **Display** (600, 24px, 1.2, -0.02em): the view title in the workspace header. One per view.
- **Headline** (600, 17px, 1.3): the record name in the reading panel and analysis section heads.
- **Title** (550, 13px, 1.4): record names in the register, nav items, buttons, tabs.
- **Body** (400, 13px, 1.55): descriptions, panel prose, help text. Prose caps at 68ch; register
  cells are not prose and may run to the column edge.
- **Label** (550, 11px, 0.02em, uppercase): column heads, facet group names, chips, badges.
- **Data** (400, 12px, tabular): counts, day deltas, line totals, paths, plugin ids.

### Named Rules

**The One-Family Rule.** No display face, no serif, anywhere. If a heading needs more presence it
gets weight and size, not a second family.

**The Compressed-Scale Rule.** Register type deliberately runs 11 / 12 / 13px with no ratio
between the steps: at 34px rows, size separates label from value from data, and weight and colour
carry the hierarchy. Real scale contrast lives above the register, in the 24px view title and the
17px panel headline.

**The Tabular Rule.** Any number that can change between rows or renders is JetBrains Mono with
`font-variant-numeric: tabular-nums`, right-aligned in the register.

**The Sentence Rule.** Uppercase is for labels of 3 words or fewer. Everything else is sentence
case, including buttons and chips.

## Layout

A three-zone workspace: a fixed 220px rail, a scrolling register, and a right reading panel that
overlays at 480px. The register column is fluid with a 1440px comfortable target and must hold at
1280px with no horizontal scroll on the table's first five columns.

- **Grid:** 4px base. Legal gaps are 4, 8, 12, 16, 20, 24, 32, 40. Nothing lands between them.
- **Workspace padding:** 20px inside the rail, 24px on the register's left and right edges.
- **Header band:** 56px tall, hairline-ruled at the bottom, holding the view title, the record
  count, and the view switcher. It does not scroll away; the register scrolls under it.
- **Facet column:** facets live in a sticky 200px column left of the register, not in a top bar.
  Each group is a `<details>` with its options as 24px selectable rows (6px radius, accent wash
  and an accent dot when chosen). A group with more than five options collapses to a 30px select
  instead of a long row list. Below 1080px the column wraps into rows above the register.
- **Register bar:** one 30px row above the register holding search, the record count, and the
  table/card switch. Nothing else goes in it.
- **Register rows:** 34px, hairline divider, 10px horizontal cell padding, sticky column heads.
  The register scrolls inside its own wrapper below its 860px minimum width, so the page body
  never scrolls sideways and the rail and header stay put.
- **Rhythm:** more space above a section heading (24px) than below it (12px), everywhere.
- **Responsive:** at 1080px the facet chips wrap to a second 40px row. At 860px the rail collapses
  to a 48px icon strip and the panel goes full width. At 640px the register drops the gloss and
  stat columns and keeps name, band dot, and last-used. Type sizes never change with viewport.

### Named Rules

**The Equal-Height Rule.** Every control in the register bar is 30px tall, and so is every select
in the facet column. A control that cannot be 30px does not belong in either.

## Elevation & Depth

Flat by default, layered tonally. Structure comes from hairlines and the canvas/surface/panel
tonal order, not from shadows. Only two things in the product actually float: the reading panel
and any menu popover. Both get one shadow and no other decoration.

### Shadow Vocabulary

- **Float** (`box-shadow: 0 1px 2px rgba(20,20,18,.04), 0 12px 32px rgba(20,20,18,.10)`): the
  reading panel and dropdown menus. In dark mode the same geometry at `rgba(0,0,0,.45)`.
- **Nub** (`box-shadow: 0 1px 2px rgba(20,20,18,.06)`): the selected face of a segmented control,
  which is the one element that reads as physically raised.

### Named Rules

**The Flat Register Rule.** Rows and cards never lift on hover. Hover is a background change
(`{colors.surface}` over canvas) and nothing else. No translate, no shadow, no scale.

## Shapes

Small, consistent radii and hairline strokes. 4px on badges and dots' containers, 6px on every
control (buttons, chips, inputs, menu items), 8px on panels and cards, 10px on the reading panel
edge. Nothing is a pill except the usage dot itself, which is a 6px circle.

Borders are 1px, `{colors.edge}` for controls and `{colors.hairline}` for row dividers. A dashed
1px border is the non-color carrier for "thin" or "inferred" — the analysis grid uses it, and so
does any value the sidecar guessed.

### Named Rules

**The No-Pill Rule.** The previous design's 999px chips, buttons, and search field are the
anti-reference. Everything interactive is 6px.

## Components

### Buttons

- **Shape:** 6px radius (`{rounded.sm}`), 30px tall, 13px/550 label.
- **Primary:** ink fill, surface text, used at most once per view (the empty-state reset).
- **Secondary:** surface fill, 1px `{colors.edge}`, ink text. The default button.
- **Ghost:** transparent, ink-2 text, used inside the panel and the filter bar.
- **Hover / Focus:** hover shifts background one tonal step (`{colors.raise}`); focus is a 2px
  `{colors.accent}` ring at 2px offset. 140ms on background and border, nothing else.

### Chips

- **Style:** 6px radius, 1px `{colors.edge}`, surface fill, 11px uppercase label, 24px tall.
- **State:** selected is `{colors.accent-wash}` fill, `{colors.accent-edge}` border, accent text,
  plus a leading check glyph so selection is not color-only. A chip carrying a count shows it in
  JetBrains Mono after the label in `{colors.ink-3}`.

### Identity marks

The `Author` column, the card badge and the panel's `Written by` row all lead with one 16px mark:
a 4px radius square (the badge radius), 1px `{colors.edge}`, `{colors.raise}` fill, glyph in
`{colors.ink-2}`.

- **Monochrome, always.** Brand color is refused here. Seventeen brands' palettes on 426 rows is
  confetti, and it would take the accent's only job — showing what is current. An 11px silhouette
  is read by shape, not hue.
- **Mark or monogram.** A drawn silhouette exists only where it can be drawn faithfully; every
  other identity gets its initials at 8px/550, taken from the name's own capitals (`PostHog` is
  PH). A letterform pretending to be a logo is a monogram, so it is one.
- **Assumed authorship is dashed.** Where the author was inferred rather than declared, the ring
  is dashed. The tool does not dress a guess as a fact.

### Cards / Containers

- **Corner Style:** 8px (`{rounded.md}`).
- **Background:** `{colors.surface}` on canvas.
- **Border:** 1px `{colors.hairline}`. **Shadow:** none at rest; see the Flat Register Rule.
- **Internal Padding:** 16px, 12px on compact cards.

### Inputs / Fields

- **Style:** surface fill, 1px `{colors.edge}`, 6px radius, 30px tall, 13px text, leading 14px
  icon at 10px inset.
- **Focus:** border becomes `{colors.accent}` with a 3px `{colors.accent-wash}` halo. No glow.
- **Empty / Disabled:** placeholder in `{colors.ink-3}`; disabled controls take `{colors.raise}`
  fill, ink-3 text, and keep their border.

### Navigation

- **Style:** the rail is `{colors.panel}` with a 1px right hairline. Items are 13px/550, 5px 8px,
  6px radius, with a 16px icon and a trailing count in JetBrains Mono.
- **States:** hover `{colors.raise}`; current destination is `{colors.raise}` fill with ink text
  and a 2px accent bar on its left edge, so current is not color-only.
- **Mobile:** below 860px the rail collapses to a 48px icon strip with the same states.

### Signature Component: the band strip

The product's spine. A row of five tabs — All, then Never called, Gone quiet, In rotation, No
record — each with a
JetBrains Mono count, sitting directly above the register. The selected tab carries ink text and a 2px
accent underline flush with the register's top hairline; unselected tabs are ink-3. The strip is
always visible, never collapses into a menu, and always opens on the most neglected non-empty
band — `All` leads the strip as the widest scope, but it is not the default; opening on everything
would delete the reason the strip exists. It is a statement of what the tool is for, so it never moves into the facet bar.

### Signature Component: the record row

34px, hairline divider, and a fixed reading order: a 6px usage dot, the skill name (13px/550 ink),
flags as chips, the gloss (13px ink-2, truncated with a title attribute), then right-aligned data
cells in JetBrains Mono. Hover fills with `{colors.surface}`; the open record fills with
`{colors.accent-wash}` and takes a 2px accent bar on its left edge. The dot uses fill for state
(solid live, solid clay, hollow gray for no record) so the three states differ in shape as well as
hue.

## Do's and Don'ts

### Do:

- **Do** keep every register-bar control at 30px and every register row at 34px.
- **Do** render counts, day deltas, and paths in JetBrains Mono with tabular figures.
- **Do** give every state a second carrier: a word, a dot fill, a dashed border, or an edge bar.
- **Do** state provenance where a value was inferred, in the panel and in the analysis notes.
- **Do** keep hover cheap: background only, 140ms, no transform.

### Don't:

- **Don't** introduce a serif or any second family. Weight and size carry hierarchy.
- **Don't** use 999px radii. Controls are 6px; the usage dot is the only circle.
- **Don't** dress facet options as bare native radios. The column stays, the controls wear the
  register's own row language.
- **Don't** lift rows or cards on hover, and don't add shadows to anything that is not floating.
- **Don't** paint a large region in the accent, or use the accent for anything but current,
  selected, focused, or a path link.
- **Don't** show a zero where there is no evidence. Absent data is an em dash in ink-3.
