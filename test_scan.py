#!/usr/bin/env python3
"""Tests for scan.py. Standard library unittest, no new dependency.

    python3 test_scan.py            # the invariants, on any machine
    python3 test_scan.py -v

Two kinds of test live here and the split is the point.

`Invariant*` classes pin the rules the tickets decided: the one-level glob, the exclusion
prefixes, the id shape, the frontmatter repair, the reference guards, the three usage states,
`prune()`'s treatment of zero. They build their own fixtures in a temp directory and pass on
any machine, including a teammate's.

`LiveLibrary` pins the counts CLAUDE.md asks for - 426 entries, 167 global, 257 plugin, 2 repo,
the parse statuses, the orchestration candidates. Those numbers describe one person's `~/.claude`
and nobody else's, so the class **skips itself** unless `data/skills.json` already exists and was
generated from that library. Run `python3 scan.py` first to arm it. Asserting them
unconditionally would hand every teammate a red suite on a correct scan, which is the same
mistake as reading a blank usage record as a zero.

`LiveCategorized` is the same idea one level in: it pins what ticket 013's pass produced, and
skips unless `data/sidecar.json` is also present. That file is gitignored and regenerable, so
deleting it must not turn a correct scan red.
"""

import json
import os
import shutil
import tempfile
import unittest

import scan


HERE = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT = os.path.join(HERE, "data", "skills.json")
SIDECAR = os.path.join(HERE, "data", "sidecar.json")

# The library these counts describe. LiveLibrary skips unless the snapshot on disk matches.
EXPECTED = {"entries": 426, "global": 167, "plugin": 257, "repo": 2}


def skill(root, name, front="", body="body\n"):
    """Write <root>/<name>/SKILL.md and return the path."""
    d = os.path.join(root, name)
    os.makedirs(d, exist_ok=True)
    f = os.path.join(d, "SKILL.md")
    with open(f, "w") as fh:
        fh.write("---\n%s\n---\n%s" % (front.strip("\n"), body) if front else body)
    return f


class Fixture(unittest.TestCase):
    """A temp ~/.claude/skills, with scan.py's module globals pointed at it."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "skills")
        os.makedirs(self.root)
        self.saved = {k: getattr(scan, k) for k in
                      ("GLOBAL_ROOT", "REPO_ROOT", "COMMANDS_ROOT", "PLUGINS_DIR", "SETTINGS",
                       "SKILL_LOCK")}
        scan.GLOBAL_ROOT = self.root
        # Every other root points somewhere absent, so a fixture describes only what it wrote.
        for k in ("REPO_ROOT", "COMMANDS_ROOT", "PLUGINS_DIR", "SETTINGS", "SKILL_LOCK"):
            setattr(scan, k, os.path.join(self.tmp, "absent-" + k.lower()))
        self.errors = list(scan.SCAN_ERRORS)
        del scan.SCAN_ERRORS[:]

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(scan, k, v)
        del scan.SCAN_ERRORS[:]
        scan.SCAN_ERRORS.extend(self.errors)
        shutil.rmtree(self.tmp, ignore_errors=True)


# ---------------------------------------------------------------- enumeration (004, 005)

class InvariantEnumeration(Fixture):

    def test_one_level_only(self):
        """005 section 0: exactly one level. A recursive walk over-collects 29 non-skills."""
        skill(self.root, "real")
        nested = os.path.join(self.root, "real", "upstream", "vendored")
        os.makedirs(nested)
        open(os.path.join(nested, "SKILL.md"), "w").write("body\n")
        self.assertEqual([os.path.basename(os.path.dirname(f))
                          for f in scan.global_skill_files()], ["real"])

    def test_exclusions_are_path_prefix_rules(self):
        """004: five *-workspace scaffolds and .git, excluded by name, not by content."""
        for name in ("keeper", "design-workspace", ".git", ".hidden"):
            skill(self.root, name)
        self.assertEqual([os.path.basename(os.path.dirname(f))
                          for f in scan.global_skill_files()], ["keeper"])

    def test_directory_without_skill_md_is_not_an_entry(self):
        os.makedirs(os.path.join(self.root, "empty-dir"))
        skill(self.root, "keeper")
        self.assertEqual(len(scan.global_skill_files()), 1)

    def test_absent_root_is_empty_not_a_traceback(self):
        """007 amendment: a fresh machine has no ~/.claude/skills and must still scan."""
        scan.GLOBAL_ROOT = os.path.join(self.tmp, "gone")
        self.assertEqual(scan.global_skill_files(), [])
        self.assertEqual([e["stage"] for e in scan.SCAN_ERRORS], ["global_root"])

    def test_absent_roots_produce_a_whole_empty_snapshot(self):
        """The first-run state the page renders. Zero entries, zero exceptions."""
        scan.GLOBAL_ROOT = os.path.join(self.tmp, "gone")
        entries, roots, plugins = scan.collect_entries()
        self.assertEqual(entries, [])
        self.assertEqual(plugins, [])
        self.assertEqual(scan.command_vocabulary(), [])


# ---------------------------------------------------------------- identity (004)

class InvariantIdentity(Fixture):

    def test_id_shape_per_source(self):
        """004: the key is the directory path; the display id is name / plugin:name / repo:name."""
        f = skill(self.root, "prime")
        plugin = {"name": "vercel", "key": "vercel@1", "version": "1", "marketplace": "m",
                  "last_updated": None, "_author": None, "_author_source": "plugin",
                  "_repository": None}
        self.assertEqual(scan.build_entry(f, "global")["id"], "prime")
        self.assertEqual(scan.build_entry(f, "plugin", plugin=plugin)["id"], "vercel:prime")
        self.assertEqual(scan.build_entry(f, "repo")["id"], "repo:prime")

    def test_id_comes_from_the_directory_not_the_frontmatter(self):
        """004: frontmatter `name` disagrees with the dirname on 8 files. The dirname wins,
        and the disagreement is recorded rather than silently resolved."""
        f = skill(self.root, "kaparthy-guidelines", front="name: karpathy-guidelines")
        e = scan.build_entry(f, "global")
        self.assertEqual(e["id"], "kaparthy-guidelines")
        self.assertEqual(e["declared_name"], "karpathy-guidelines")

    def test_agreeing_name_is_not_recorded(self):
        f = skill(self.root, "prime", front="name: prime")
        self.assertIsNone(scan.build_entry(f, "global")["declared_name"])

    def test_unreadable_file_is_skipped_not_fatal(self):
        missing = os.path.join(self.root, "ghost", "SKILL.md")
        self.assertIsNone(scan.build_entry(missing, "global"))
        self.assertEqual([e["stage"] for e in scan.SCAN_ERRORS], ["read"])


# ---------------------------------------------------------------- frontmatter (004)

class InvariantFrontmatter(unittest.TestCase):

    def parse(self, text):
        return scan.parse_frontmatter(text, "<test>")

    def test_block_scalar_description_survives(self):
        """004: regex silently returned the wrong description on 606 files, capturing the
        `|` sigil. This is the case that decided PyYAML over regex."""
        fm, _, _, status = self.parse("---\ndescription: |\n  Real text.\n---\nbody\n")
        self.assertEqual(status, "ok")
        self.assertEqual(fm["description"].strip(), "Real text.")

    def test_force_quote_repairs_a_yaml_reject(self):
        """A bare `@` cannot open a plain scalar. 004 measured this repair at 21 files."""
        fm, _, _, status = self.parse("---\nname: x\nallowed-tools: @repo/*\n---\nbody\n")
        self.assertEqual(status, "repaired")
        self.assertEqual(fm["allowed-tools"], "@repo/*")

    def test_repaired_status_is_the_health_flag(self):
        """009: `frontmatter_repaired` is untidy, not broken. The harness loads these files."""
        self.assertEqual(scan.force_quote("k: @v"), 'k: "@v"')
        self.assertEqual(scan.force_quote('k: "@v"'), 'k: "@v"')   # already quoted, left alone
        self.assertEqual(scan.force_quote("k: |"), "k: |")         # block scalar, left alone

    def test_no_frontmatter_is_fallback_not_a_crash(self):
        fm, front, body, status = self.parse("# Just a heading\n")
        self.assertEqual((fm, front, status), ({}, "", "fallback"))
        self.assertEqual(body, "# Just a heading\n")


# ---------------------------------------------------------------- references (003, 006 Q12)

class InvariantReferences(unittest.TestCase):

    VOCAB = {"ux-flow", "checkout", "pricing", "marketing-sprint", "posthog:exploring-llm-costs",
             "exploring-llm-costs"}

    def refs(self, text, self_name="root"):
        return scan.refs_in(text, self.VOCAB, self_name)

    def test_url_path_segments_are_not_skill_references(self):
        """006 Q12. Without the guard, `/checkout` and `/pricing` inside a URL matched real
        skill names and took edges from 156 to 391."""
        self.assertEqual(self.refs("See `https://example.com/checkout` and `/pricing/plans`."),
                         set())

    def test_a_bare_slash_reference_still_counts(self):
        self.assertEqual(self.refs("Then run /ux-flow to continue."), {"ux-flow"})

    def test_a_trailing_period_suppresses_the_reference(self):
        """The known cost of 006 Q12's `(?![/.])` guard, pinned rather than fixed. Measured
        2026-08-24 across all 426 files: 5 entries write a sentence-final `/name.`, and all 5
        are the skill naming itself, which `refs_in` discards anyway. Zero real edges lost.
        Revisit only if that count stops being zero."""
        self.assertEqual(self.refs("Then run /ux-flow."), set())
        self.assertEqual(self.refs("Then run /ux-flow, then stop."), {"ux-flow"})

    def test_backtick_reference_needs_an_invocation_verb(self):
        """003: unconditional backtick matching inflates candidates from 44 to 106. The gate
        is a line carrying an invocation verb or a Step/Phase heading."""
        self.assertEqual(self.refs("The `ux-flow` document is long."), set())
        self.assertEqual(self.refs("Step 2: run `ux-flow` first."), {"ux-flow"})

    def test_qualified_and_bare_forms_are_one_edge(self):
        """A body naming both forms means one edge, not two. The qualified form wins."""
        self.assertEqual(self.refs("Call /posthog:exploring-llm-costs, i.e. `/exploring-llm-costs`."),
                         {"posthog:exploring-llm-costs"})

    def test_self_reference_is_dropped(self):
        self.assertEqual(self.refs("Run /ux-flow.", self_name="ux-flow"), set())

    def test_footer_stripping_is_load_bearing(self):
        """003: pm-skills stamps a Dependencies footer on every leaf, inflating ~30 leaves
        to four references each."""
        body = "# Real\n\nNothing here.\n\n## Dependencies\n\nRun /ux-flow and /marketing-sprint.\n"
        self.assertEqual(self.refs(scan.strip_body(body)), set())

    def test_fenced_code_is_stripped(self):
        self.assertEqual(self.refs(scan.strip_body("```\n/ux-flow\n```\n")), set())

    def test_step_section_ends_at_same_or_shallower_heading(self):
        """012: ending a step at its own first subheading dropped a real target on
        launch-sprint. A section runs to the next heading at the same or a shallower level."""
        body = ("## Step 6: Comms\n\nIntro.\n\n### Build-in-public post\n\n"
                "Run /marketing-sprint here.\n\n## Step 7: Done\n\nNothing.\n")
        blocks = scan.step_blocks(body, self.VOCAB, "root")
        self.assertEqual([t for t, _ in blocks], ["Step 6: Comms", "Step 7: Done"])
        self.assertEqual(blocks[0][1], ["marketing-sprint"])
        self.assertEqual(blocks[1][1], [])

    def test_step_blocks_are_document_order_not_alphabetical(self):
        """012: the whole feature is the order the author wrote, which `delegates_to` discards."""
        body = "## Step 1\n\nRun /ux-flow.\n\n## Step 2\n\nRun /marketing-sprint.\n"
        self.assertEqual([t for t, _ in scan.step_blocks(body, self.VOCAB, "root")],
                         ["Step 1", "Step 2"])

    def test_clean_title_strips_authored_markdown(self):
        self.assertEqual(scan.clean_title("Step 8: Roadmap *(client mode only)*"),
                         "Step 8: Roadmap (client mode only)")


# ---------------------------------------------------------------- usage (002)

class InvariantUsage(unittest.TestCase):
    """002's three-state rule, generalised for other machines by 007.

    `used` is a count. `never_used` needs history that reaches further back than transcripts
    already do. Everything else is `no_data`, because a transcript-derived zero can never mean
    never used: transcripts are on a proven 30-day whole-file delete.
    """

    NOW = "2026-08-24T00:00:00Z"
    DEEP = ("2026-03-04T00:00:00Z", "2026-08-18T00:00:00Z")     # 167 days of history
    SHALLOW = ("2026-07-25T00:00:00Z", "2026-08-18T00:00:00Z")  # inside the transcript window
    TRANSCRIPTS = ("2026-07-25T00:00:00Z", "2026-08-18T00:00:00Z")

    def state(self, source="global", history=None, store=None):
        e = {"name": "x", "id": "x", "source": source}
        scan.attach_usage([e], store or {}, self.NOW, self.TRANSCRIPTS,
                          history if history is not None else self.DEEP)
        return e["usage"]

    def test_deep_history_and_no_record_is_never_used(self):
        self.assertEqual(self.state()["state"], "never_used")

    def test_shallow_history_and_no_record_is_no_data(self):
        """A history that adds nothing beyond the 30-day window proves nothing."""
        self.assertEqual(self.state(history=self.SHALLOW)["state"], "no_data")

    def test_absent_history_is_no_data(self):
        self.assertEqual(self.state(history=(None, None))["state"], "no_data")

    def test_plugin_silence_is_never_never_used(self):
        """The only certain evidence channel for a plugin skill is the 30-day window."""
        self.assertEqual(self.state(source="plugin")["state"], "no_data")

    def test_no_data_reports_no_count_rather_than_zero(self):
        """PRODUCT.md: absent data reads as unknown, never as zero."""
        self.assertIsNone(self.state(history=(None, None))["total_count"])

    def test_never_used_reports_zero_because_zero_is_the_finding(self):
        self.assertEqual(self.state()["total_count"], 0)

    def test_a_record_makes_it_used(self):
        rec = scan.blank_usage()
        rec["tool_calls"] = 3
        rec["tool_calls_last_at"] = "2026-08-20T00:00:00Z"
        u = self.state(store={"x": rec})
        self.assertEqual((u["state"], u["total_count"], u["sources"]), ("used", 3, ["tool_call"]))
        self.assertEqual(u["days_since_last_use"], 4)

    def test_ambiguous_attribution_is_flagged_on_every_candidate(self):
        """005: hook injections carry the bare name, tool calls carry the prefix, so the count
        is written to every candidate and flagged. Never sum usage across entries."""
        a = {"name": "agent-browser", "id": "agent-browser", "source": "global"}
        b = {"name": "agent-browser", "id": "vercel:agent-browser", "source": "plugin"}
        scan.attach_usage([a, b], {}, self.NOW, self.TRANSCRIPTS, self.DEEP)
        for e in (a, b):
            self.assertEqual(e["usage"]["attribution"], "ambiguous")
            self.assertEqual(e["usage"]["attribution_candidates"],
                             ["agent-browser", "vercel:agent-browser"])

    def test_bump_normalises_the_prefix_but_keeps_the_alias(self):
        store = {}
        scan.bump(store, "vercel:nextjs", "injections", "2026-08-01T00:00:00Z")
        self.assertEqual(list(store), ["nextjs"])
        self.assertEqual(store["nextjs"]["aliases"], {"vercel:nextjs"})


# ---------------------------------------------------------------- health (009)

class InvariantHealth(unittest.TestCase):

    def entry(self, **kw):
        e = {"source": "global", "parse_status": "ok", "declared_name": None,
             "delegates_to_unresolved": [], "_front": "", "_body": "", "body_lines": 100,
             "description": "Use this skill when the user asks."}
        e.update(kw)
        scan.attach_health([e])
        return e

    def test_plugin_entries_are_excluded_before_any_check(self):
        """009: the MAP puts improving plugin skills out of scope, and an unactionable defect
        list is noise."""
        self.assertEqual(self.entry(source="plugin", parse_status="repaired")["health_flags"], [])

    def test_each_mechanical_flag_fires(self):
        self.assertIn("frontmatter_repaired", self.entry(parse_status="repaired")["health_flags"])
        self.assertIn("name_mismatch", self.entry(declared_name="other")["health_flags"])
        self.assertIn("missing_target", self.entry(delegates_to_unresolved=["gone"])["health_flags"])
        self.assertIn("foreign_marker", self.entry(_body=r"see C:\Users\x")["health_flags"])

    def test_drive_letter_guard(self):
        """009: the unguarded pattern flagged 48 of 169, because `s://` matches inside every
        `https://`. Guarded it flags 1, which is correct."""
        self.assertEqual(self.entry(_body="https://example.com")["health_flags"], [])

    def test_thin_body_only_nominates_for_adjudication(self):
        """Tier two is suggestive, never a flag: 009 rejected body length as quality."""
        e = self.entry(body_lines=5)
        self.assertEqual(e["health_flags"], [])
        self.assertTrue(e["health_candidate"])

    def test_trigger_phrasing_clears_the_nomination(self):
        self.assertFalse(self.entry()["health_candidate"])
        self.assertTrue(self.entry(description="Makes charts.")["health_candidate"])


# ---------------------------------------------------------------- duplicates (011)

class InvariantDuplicates(unittest.TestCase):

    def entry(self, entry_id, **kw):
        e = {"id": entry_id, "usage": {"total_count": 0, "days_since_last_use": None},
             "source": "global", "has_resources": False, "body_lines": 10,
             "parse_status": "ok", "health_flags": [], "_front": "", "_body": "same"}
        e.update(kw)
        return e

    def test_group_key_strips_the_plugin_prefix(self):
        """011: grouping on the id with the prefix stripped is what finds the vercel twins."""
        a, b = self.entry("vercel:nextjs"), self.entry("vercel-plugin:nextjs")
        groups = scan.attach_duplicates([a, b])
        self.assertEqual([g["key"] for g in groups], ["nextjs"])
        self.assertEqual(a["twin_group"], "nextjs")

    def test_a_lone_entry_is_not_a_group(self):
        self.assertEqual(scan.attach_duplicates([self.entry("nextjs")]), [])

    def test_byte_identical_is_reported(self):
        groups = scan.attach_duplicates([self.entry("a:x"), self.entry("b:x")])
        self.assertTrue(groups[0]["identical"])

    def test_it_refuses_to_recommend_when_nothing_separates_the_copies(self):
        """011: the recommendation names the single deciding criterion, or declines."""
        groups = scan.attach_duplicates([self.entry("a:x"), self.entry("b:x")])
        self.assertIsNone(groups[0]["keep"])
        self.assertIsNone(groups[0]["why"])

    def test_it_recommends_on_the_first_differing_criterion(self):
        a = self.entry("a:x", usage={"total_count": 9, "days_since_last_use": 1})
        b = self.entry("b:x", _body="different")
        groups = scan.attach_duplicates([a, b])
        self.assertEqual(groups[0]["keep"], "a:x")
        self.assertIsNotNone(groups[0]["why"])
        self.assertFalse(groups[0]["identical"])


# ---------------------------------------------------------------- payload (005)

class InvariantPayload(unittest.TestCase):

    def test_prune_drops_empties(self):
        self.assertEqual(scan.prune({"a": None, "b": False, "c": "", "d": [], "e": {}}), {})

    def test_prune_keeps_zero(self):
        """A usage count of 0 is the never_used finding, not an absence."""
        self.assertEqual(scan.prune({"total_count": 0}), {"total_count": 0})

    def test_prune_keeps_true_and_content(self):
        self.assertEqual(scan.prune({"a": True, "b": "x", "c": [1]}),
                         {"a": True, "b": "x", "c": [1]})

    def test_payload_carries_scan_errors_for_the_first_run_state(self):
        """The empty-library page is the only reader, and without this it cannot say why."""
        snap = {"snapshot_generated_at": "x", "counts": {}, "usage_sources": {},
                "releases": [], "duplicates": [], "entries": [],
                "scan_errors": [{"path": "p", "stage": "global_root", "error": "absent"}]}
        self.assertEqual(scan.ui_payload(snap)["scan_errors"], snap["scan_errors"])

    def test_payload_restores_nothing_the_page_indexes_into_blindly(self):
        """CLAUDE.md's rule, checked from this side: any field the page indexes into must be
        in UI_ENTRY_FIELDS, or it silently disappears from the built page."""
        for field in ("delegates_to", "reached_via", "delegates_to_unresolved",
                      "health_flags", "reach_flags"):
            self.assertIn(field, scan.UI_ENTRY_FIELDS)


# ---------------------------------------------------------------- categorize pass (013)

class InvariantCategorize(unittest.TestCase):
    """`--categorize` prepares the pass; a model outside the tool performs it."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.saved = {k: getattr(scan, k) for k in ("SIDECAR", "OVERRIDES", "CATEGORIZE")}
        scan.SIDECAR = os.path.join(self.tmp, "sidecar.json")
        scan.OVERRIDES = os.path.join(self.tmp, "overrides.json")
        scan.CATEGORIZE = os.path.join(self.tmp, "categorize.md")

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(scan, k, v)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def sidecar(self, entries):
        with open(scan.SIDECAR, "w") as f:
            json.dump({"schema_version": 1, "entries": entries}, f)

    def entry(self, entry_id="x", **kw):
        e = {"id": entry_id, "name": entry_id, "source": "global", "skill_file": "/tmp/%s" % entry_id,
             "description": "d", "body_lines": 5, "kind": None, "domain": None,
             "domain_secondary": None, "gloss": None, "category_status": "uncategorized",
             "category_source": "none", "orchestration_degree": 0, "orchestration_class": None,
             "orchestration_reason": None, "orchestration_source": "rule", "orchestration_verdict": False,
             "health_candidate": False, "health_flags": [], "health_verdict": None,
             "health_source": "none", "reach_flags": [], "reach_verdict": None,
             "reach_source": "none", "publishable": False, "plugin": None,
             "delegates_to": [], "reached_via": [], "steps": []}
        e.update(kw)
        return e

    def test_pools_are_the_four_sections(self):
        entries = [self.entry("a"),
                   self.entry("b", orchestration_degree=2),
                   self.entry("c", health_candidate=True),
                   self.entry("d", reach_flags=["network"])]
        self.assertEqual({k: [e["id"] for e in v] for k, v in scan.categorize_pools(entries)},
                         {"category": ["a", "b", "c", "d"], "orchestration": ["b"],
                          "health": ["c"], "reach": ["d"]})

    def test_an_answered_entry_leaves_its_pool(self):
        """013 decision 5: a re-run after adding four skills is a four-entry prompt."""
        entries = [self.entry("a"), self.entry("b")]
        self.sidecar({"a": {"kind": "Reference"}})
        pools = dict(scan.categorize_pools(entries))
        self.assertEqual([e["id"] for e in pools["category"]], ["b"])

    def test_a_non_sharp_reach_flag_is_not_in_the_pool(self):
        """010: only the four that mean the skill can act outside its own file."""
        pools = dict(scan.categorize_pools([self.entry("a", reach_flags=["claude_home"])]))
        self.assertEqual(pools["reach"], [])

    def test_nothing_is_written_when_every_pool_is_empty(self):
        """013 decision 6: a command that emits an empty prompt gets pasted anyway."""
        entries = [self.entry("a", kind="Reference", category_status="assigned")]
        self.assertEqual(scan.write_categorize(entries, "2026-08-24T00:00:00Z"),
                         {"category": 0, "orchestration": 0, "health": 0, "reach": 0})
        self.assertFalse(os.path.exists(scan.CATEGORIZE))

    def test_the_prompt_never_carries_a_body(self):
        """013 decision 3. Inlining the core pool's bodies is 36,828 lines."""
        e = self.entry("a", description="what it does")
        e["_body"] = "SECRET BODY TEXT"
        scan.write_categorize([e], "2026-08-24T00:00:00Z")
        with open(scan.CATEGORIZE) as f:
            text = f.read()
        self.assertIn("what it does", text)
        self.assertNotIn("SECRET BODY TEXT", text)

    def test_the_prompt_carries_the_path_so_section_four_can_open_it(self):
        scan.write_categorize([self.entry("a", reach_flags=["destructive"])],
                              "2026-08-24T00:00:00Z")
        with open(scan.CATEGORIZE) as f:
            self.assertIn("path: /tmp/a", f.read())

    def test_a_skipped_section_is_omitted_not_left_empty(self):
        scan.write_categorize([self.entry("a")], "2026-08-24T00:00:00Z")
        with open(scan.CATEGORIZE) as f:
            text = f.read()
        self.assertIn("Section 1", text)
        self.assertNotIn("Section 4", text)

    def test_merge_precedence_sidecar_then_override(self):
        """005's precedence, extended to the two fields 013 added."""
        e = self.entry("a")
        self.sidecar({"a": {"kind": "Reference", "gloss": "from sidecar",
                            "reach_verdict": "no reach"}})
        with open(scan.OVERRIDES, "w") as f:
            json.dump({"entries": {"a": {"gloss": "from override"}}}, f)
        scan.merge_categories([e])
        self.assertEqual(e["gloss"], "from override")
        self.assertEqual(e["kind"], "Reference")
        self.assertEqual(e["category_source"], "llm")
        self.assertEqual(e["reach_verdict"], "no reach")
        self.assertEqual(e["reach_source"], "adjudicated")

    def test_a_missing_sidecar_never_fails_the_scan(self):
        """005: a skill missing from the sidecar shows uncategorized and the scan continues."""
        e = self.entry("a")
        scan.merge_categories([e])
        self.assertEqual(e["category_status"], "uncategorized")
        self.assertIsNone(e["gloss"])

    def test_gloss_and_reach_verdict_reach_the_page(self):
        for field in ("gloss", "reach_verdict"):
            self.assertIn(field, scan.UI_ENTRY_FIELDS)


# ---------------------------------------------------------------- the live library

def live_snapshot():
    """The snapshot on disk, but only if it is the library EXPECTED describes."""
    try:
        with open(SNAPSHOT) as f:
            snap = json.load(f)
    except (OSError, ValueError):
        return None
    counts = snap.get("counts", {})
    return snap if all(counts.get(k) == v for k, v in EXPECTED.items()) else None


@unittest.skipIf(live_snapshot() is None,
                 "no data/skills.json from the %d-entry library; run python3 scan.py"
                 % EXPECTED["entries"])
class LiveLibrary(unittest.TestCase):
    """The counts the tickets assert, checked against a real scan.

    Machine-specific on purpose, and skipped everywhere else. These are regression bait: if a
    change to the heuristics moves one of them, that is the signal, and the fix is either the
    code or this number plus the ticket that explains it.
    """

    @classmethod
    def setUpClass(cls):
        cls.snap = live_snapshot()
        cls.entries = cls.snap["entries"]

    def test_inventory(self):
        """005: 426 entries via a strict one-level glob. Not 1362 and not 428."""
        for key, want in EXPECTED.items():
            self.assertEqual(self.snap["counts"][key], want, key)
        self.assertEqual(len(self.entries), EXPECTED["entries"])

    def test_ids_are_unique(self):
        """004: the whole reason the id is not the bare name. It collides on 96 names."""
        ids = [e["id"] for e in self.entries]
        self.assertEqual(len(set(ids)), len(ids))

    def test_bare_names_do_collide(self):
        """The measurement that forced the id shape, asserted so it stays true of the data."""
        names = [e["name"] for e in self.entries]
        self.assertLess(len(set(names)), len(names))

    def test_parse_status(self):
        """004's hybrid: PyYAML plus force-quote repair. No file falls all the way through."""
        got = {}
        for e in self.entries:
            got[e["parse_status"]] = got.get(e["parse_status"], 0) + 1
        self.assertEqual(got, {"ok": 409, "repaired": 17})

    def test_orchestration(self):
        """003 and 006 Q12: 22 mechanical candidates, 10 the rule verdict clears."""
        self.assertEqual(sum(1 for e in self.entries if e["orchestration_degree"] >= 2), 22)
        self.assertEqual(sum(1 for e in self.entries if e["orchestration_verdict"]), 10)

    def test_every_orchestrator_carries_steps(self):
        """012: `steps` is gated on the verdict, so 10 of 426 entries have it."""
        self.assertEqual(sum(1 for e in self.entries if e.get("steps")), 10)

    def test_health(self):
        """009: 24 of Eli's 169 flagged, 43 nominated for adjudication."""
        self.assertEqual(self.snap["counts"]["flagged"], 24)
        self.assertEqual(self.snap["counts"]["health_candidates"], 43)
        self.assertFalse([e for e in self.entries
                          if e["source"] == "plugin" and e["health_flags"]])

    def test_reach(self):
        """010: 111 of 426, and unlike health it runs on plugin entries too."""
        self.assertEqual(self.snap["counts"]["reaching"], 111)
        self.assertTrue([e for e in self.entries
                         if e["source"] == "plugin" and e["reach_flags"]])

    def test_duplicates(self):
        """011: 27 groups covering 54 entries, 12 byte-identical."""
        groups = self.snap["duplicates"]
        self.assertEqual(len(groups), 27)
        self.assertEqual(sum(len(g["members"]) for g in groups), 54)
        self.assertEqual(sum(1 for g in groups if g["identical"]), 12)

    def test_usage_states_partition_the_library(self):
        """002's three states, and every entry is in exactly one."""
        got = {}
        for e in self.entries:
            got[e["usage"]["state"]] = got.get(e["usage"]["state"], 0) + 1
        self.assertEqual(set(got), {"used", "never_used", "no_data"})
        self.assertEqual(sum(got.values()), EXPECTED["entries"])

    def test_no_plugin_entry_is_ever_never_used(self):
        """The rule, checked against the whole library rather than one fixture."""
        self.assertFalse([e for e in self.entries
                          if e["source"] == "plugin" and e["usage"]["state"] == "never_used"])

    def test_nothing_is_publishable_by_omission(self):
        """007: allowlist only, fail closed. `publishable` is false on all 426 today."""
        self.assertFalse([e for e in self.entries if e.get("publishable")])




@unittest.skipIf(live_snapshot() is None or not os.path.exists(SIDECAR),
                 "no sidecar from the categorize pass; run python3 scan.py --categorize")
class LiveCategorized(unittest.TestCase):
    """What ticket 013's pass produced, on top of a live snapshot.

    Separate from LiveLibrary because the sidecar is gitignored: delete it and a correct scan
    still holds every count above, but nothing here is true any more. The invariants in
    InvariantCategorize cover the merge itself and pass with no sidecar at all.
    """

    @classmethod
    def setUpClass(cls):
        cls.snap = live_snapshot()
        cls.entries = cls.snap["entries"]

    def test_the_categorize_pass_has_run(self):
        """Ticket 013. This test previously asserted 169 uncategorized and no `llm` source;
        the pass landing is exactly what flipped it, which is what a live count is for."""
        self.assertEqual(self.snap["counts"]["uncategorized"], 0)
        self.assertEqual(sum(1 for e in self.entries if e["category_source"] == "llm"), 169)
        self.assertEqual(sum(1 for e in self.entries if e["orchestration_source"] == "adjudicated"), 22)
        self.assertEqual(sum(1 for e in self.entries if e["health_source"] == "adjudicated"), 43)

    def test_every_domain_and_kind_is_populated(self):
        """The symptom 013 was written about: 2 of 8 domains and 2 of 7 kinds in the facets."""
        self.assertEqual({e["domain"] for e in self.entries if e["domain"]}, set(scan.DOMAINS))
        self.assertEqual({e["kind"] for e in self.entries}, set(scan.KINDS))

    def test_kind_never_contradicts_the_adjudication(self):
        """001 defines Orchestrator as sequencing other skills, which is the same claim
        `orchestration_class: orchestrator` makes. The panel prints both, four lines apart."""
        self.assertFalse([e["id"] for e in self.entries if e["orchestration_class"]
                          and (e["kind"] == "Orchestrator") != (e["orchestration_class"] == "orchestrator")])

    def test_reach_tier_two_is_still_unrun(self):
        """013 section 4 is skippable by design and was skipped. When someone runs it, this
        is the test that tells them it landed."""
        self.assertFalse([e for e in self.entries if e.get("reach_verdict")])

if __name__ == "__main__":
    unittest.main(verbosity=2)
