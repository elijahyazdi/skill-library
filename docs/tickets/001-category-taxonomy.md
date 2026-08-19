# 001 — Category taxonomy for the library

Parent: `../MAP.md`
Label: `wayfinder:grilling` (HITL)
Blocked by: none
Status: CLOSED 2026-08-18

## Question

What is the category set the library filters by, and what rules assign a skill to one?

Constraints and known facts:

- Nothing on disk carries a category. One skill has `metadata.tags`. The taxonomy is being
  invented here, not discovered.
- The example set from the original idea was "marketing, product design, engineering,
  procurement". "Procurement" looks like a typo and needs confirming or replacing.
- The set has to cover ~1362 skills across two very different populations: Eli's ~172
  (marketing-heavy, plus rituals like `morning`, `daily-reflection`, `intentional-buy`) and
  1190 vendor skills (overwhelmingly engineering and platform-specific).
- Genuinely ambiguous cases that will test any taxonomy: `council`, `zoom-out`, `prototype`,
  `grilling`, `wayfinder`, `humanizer`, `decision-toolkit`, `intentional-buy`.

Must decide:

1. The category list, and how many is too many to be useful as a filter.
2. Single category per skill, or multiple? Multiple makes filtering richer and counting messy.
3. Whether personal/life skills get their own category or are excluded from the default view.
4. Whether vendor platform skills collapse into one "platform" category or spread across the
   same taxonomy as Eli's own.
5. Whether category is a flat list or two levels (domain, then function).

## Resolution

Resolved 2026-08-18 by grilling session. Two independent facets, not one flat list.

### Facet 1 — Domain (what work it serves)

Eight domains. **Nullable.** A null Domain displays as `Any` and means *universal*, not *unknown*.

1. Marketing
2. Product & Design
3. Engineering
4. PM & Delivery
5. Writing
6. Business & Clients
7. Personal
8. Platform — vendor/plugin skills only, subdivided by plugin (Vercel, PostHog, Sanity, Figma, …)

**Cardinality:** one primary domain per skill. An optional secondary domain may be recorded and
displayed, but is never filtered on — so counts stay sane and a domain filter never leaks.

**On `Any`:** a set of skills genuinely serve every domain equally — `xlsx`, `pdf`, `docx`, `pptx`,
`image`, `video`, `audio-transcriber`, `file-organizer`, `agent-browser`, `grilling`, `council`,
`zoom-out`, `prompt-master`. A ninth "Craft & Tools" domain was proposed and rejected: filtering it
returns an incoherent grab bag, and it would hide `xlsx` from every domain view. The Kind facet was
also considered as a substitute and rejected — Kind *scatters* that set (some are Converters, some
Thinking tools, some neither); the only thing they share is having no domain, which is the field
Kind is not. `Any` is the true statement.

**Consequence for the UI (belongs to ticket 006):** because `Any` means universal, a Domain filter
can legitimately include `Any` skills alongside the selected domain rather than hiding them.
Whether it does is a UI decision, logged in 006, not decided here.

### Facet 2 — Kind (what shape it is)

Seven kinds. **Required, strictly single.**

| Kind | Definition | Representative examples |
|---|---|---|
| Orchestrator | Sequences other skills | `feature-sprint`, `design-sprint`, `pm-orchestrator`, `growth-sprint`, `wayfinder` |
| Ritual | Runs on a calendar cadence | `morning`, `weekly`, `week-wrap`, `sunday-timeblock`, `daily-reflection` |
| Converter | Takes X, emits Y | `to-prd`, `to-issues`, `to-spec`, `docx`, `pdf`, `xlsx`, `pptx` |
| Reviewer | Judges existing work | `code-review`, `review`, `design-audit`, `seo-audit`, `qa`, `fact-checker`, `humanizer` |
| Generator | Produces a new artifact | `copywriting`, `ad-creative`, `style-tiles`, `wireframe-ready`, `image` |
| Thinking tool | Structures reasoning, no artifact | `grilling`, `council`, `zoom-out`, `decision-toolkit`, `product-lens` |
| Reference | Knowledge lookup, no action | `sanity-*-best-practices`, `remotion-best-practices`, `kaparthy-guidelines`, `brand-guidelines` |

**Tiebreak precedence, applied top-down** (many skills are genuinely two kinds — `weekly` is a
Ritual that orchestrates, `daily-reflection` is a Ritual that converts, `bug-detective` reviews
then generates):

`Orchestrator > Ritual > Converter > Reviewer > Generator > Thinking tool > Reference`

Orchestrator wins because it is the one Kind explicitly requested in the original idea. Ritual is
second because cadence is the rarer and more useful signal. Reference is last, so anything
unclassifiable lands somewhere defensible rather than in a misc bucket.

The orchestration badge from the original idea *is* this facet's top value — it falls out of the
taxonomy rather than being a bolted-on boolean.

### How categories get assigned

**Vendor/plugin skills (~1190): by rule, no LLM call.** Domain = Platform, subdivided by plugin.
Kind = Reference by default. Rationale: they are 87% of the library and almost entirely platform
reference material. Giving them full taxonomy treatment would drown the ~35 genuine Engineering
skills in ~900 vendor entries and cost an LLM pass over 1190 files to produce a facet that would
never be used.

**Eli's ~172 plus one representative sample per plugin: LLM pass.** Input per skill is the
frontmatter description plus the first 40 lines of body. Descriptions alone carry strong Domain
signal (they are long and trigger-phrase dense), but Kind is frequently only visible in the body —
`design-sprint` states its orchestration several paragraphs down. This scopes the pass to roughly
180 calls, cheap enough to re-run whenever skills are added.

**Interaction with ticket 003:** 003 is separately measuring whether Orchestrator is detectable by
grep with no LLM call. If it clears a useful accuracy bar, that Kind comes free and the LLM pass
only has to resolve the remaining six.

### Correcting a wrong category

A hand-maintained **overrides file** that the LLM pass never writes to, merged on top of the
machine-written sidecar at scan time. Rejected alternatives: re-running the pass with a better
prompt (does not converge, and a wrong call on `council` or `humanizer` is a judgment difference,
not a prompt bug) and living with it (the filter loses trust within a week and the tool dies).

### Also settled

"Procurement" from the original idea was a typo and is dropped. No procurement-shaped work exists
in the 172. Business & Clients is kept as its own domain rather than folded into PM & Delivery,
because client work (`client-intake`, `client-handoff`, `project-estimate`, `professional-brevity`,
`pricing`) is a distinct mode from delivery and gets filtered separately.

Personal is a domain rather than an orthogonal private/public flag, and ticket 007's publish gate
keys off it as the default deny. One concept, two uses — 007 does not need to invent a second field.

### Downstream effects

- **005 (schema):** needs `domain` (nullable string), `domain_secondary` (nullable, display-only),
  `kind` (required enum of 7), `plugin` (nullable, for Platform subdivision). Sidecar and overrides
  file merge order matters: overrides last.
- **006 (UI):** must decide whether `Any`-domain skills appear in every domain view. Kind is a
  first-class facet, not a badge.
- **007 (publish):** `domain == Personal` is the default-deny rule.
- **003 (orchestration):** its output maps onto Kind = Orchestrator, the top of the precedence
  order, not a separate boolean field.
