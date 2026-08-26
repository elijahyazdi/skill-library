#!/usr/bin/env python3
"""Skill Library scanner. Writes data/skills.json.

Implements the scan contract in tickets/005-snapshot-schema.md. Read that first: every
root, precedence rule and null semantic below is decided there, not here.

Never writes to any SKILL.md. Read-only is MAP decision 1.

Usage:  python3 scan.py [--out data/skills.json] [--repo PATH] [--prototype]
"""

import argparse
import collections
import datetime as dt
import getpass
import glob
import json
import os
import re
import subprocess
import sys

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required: pip3 install pyyaml")

SCHEMA_VERSION = 3  # 014: entries gained `example`, `example_from`, `example_truncated`.
SCANNER_VERSION = "1.0.0"   # tracks the release tag; SCHEMA_VERSION tracks the payload

HOME = os.path.expanduser("~")
GLOBAL_ROOT = os.path.join(HOME, ".claude", "skills")
COMMANDS_ROOT = os.path.join(HOME, ".claude", "commands")
PLUGINS_DIR = os.path.join(HOME, ".claude", "plugins")
SETTINGS = os.path.join(HOME, ".claude", "settings.json")
SKILL_LOCK = os.path.join(HOME, ".agents", ".skill-lock.json")
HISTORY = os.path.join(HOME, ".claude", "history.jsonl")
TRANSCRIPT_GLOB = os.path.join(HOME, ".claude", "projects", "*", "*.jsonl")
# A second skills checkout outside ~/.claude. This default is Eli's and contributes 2 of 426
# entries; --repo points it somewhere else, and an absent path is skipped, not an error.
REPO_ROOT = os.path.join(HOME, "Development", "claude-skills")

# Ticket 005 section 0: exactly one level. A recursive walk over-collects 29 non-skills
# (vendored upstream/ copies, a nested plugin repo copy, figma workflow-skills/).
ONE_LEVEL = "skills/*/SKILL.md"

DOMAINS = ["Marketing", "Product & Design", "Engineering", "PM & Delivery",
           "Writing", "Business & Clients", "Personal", "Platform"]
KINDS = ["Orchestrator", "Ritual", "Converter", "Reviewer",
         "Generator", "Thinking tool", "Reference"]

SCAN_ERRORS = []


def err(path, stage, e):
    SCAN_ERRORS.append({"path": path, "stage": stage, "error": str(e)})


def read_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        if default is None:
            err(path, "read_json", e)
        return default


def iso(ms=None, when=None):
    d = when or dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc)
    return d.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def parse_iso(s):
    if not s:
        return None
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


# ---------------------------------------------------------------- frontmatter

FM_SPLIT = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", re.DOTALL)
KV_LINE = re.compile(r"^([A-Za-z][\w.-]*):[ \t]+(?!\s*$)(?![|>&*])(.*\S)\s*$")
# A sequence item whose scalar opens with a YAML indicator character. `- @repo/*` is
# not a parse ambiguity, it is a hard reject: @ and ` are reserved and can never start
# a plain scalar, and * & ! % would be read as alias, anchor, tag or directive.
SEQ_INDICATOR = re.compile(r"^(\s*-[ \t]+)([@`*&!%].*\S)\s*$")


def quoted(val):
    return val.replace("\\", "\\\\").replace('"', '\\"')


def force_quote(front):
    """Repair pass for frontmatter YAML rejects.

    Quotes the scalar half of top-level key: value lines, and sequence items opening
    with a YAML indicator character, leaving block scalars and nested maps alone.
    This is the repair 004 measured at 21 files.
    """
    out = []
    for line in front.splitlines():
        m = KV_LINE.match(line)
        s = SEQ_INDICATOR.match(line)
        if m and not (m.group(2).startswith(("'", '"')) and m.group(2).endswith(("'", '"'))):
            out.append('%s: "%s"' % (m.group(1), quoted(m.group(2))))
        elif s:
            out.append('%s"%s"' % (s.group(1), quoted(s.group(2))))
        else:
            out.append(line)
    return "\n".join(out)


def parse_frontmatter(text, path):
    """Return (mapping, front_text, body, parse_status).

    PyYAML first. Regex is never the primary path: 004 measured it silently returning
    the wrong description on 606 files, because `description: |` block scalars make it
    capture the sigil.
    """
    m = FM_SPLIT.match(text)
    if not m:
        return {}, "", text, "fallback"
    front, body = m.group(1), m.group(2)
    for candidate, status in ((front, "ok"), (force_quote(front), "repaired")):
        try:
            data = yaml.safe_load(candidate)
        except yaml.YAMLError:
            continue
        if isinstance(data, dict):
            return data, front, body, status
    # Last resort: first description-looking line, flat.
    flat = {}
    for line in front.splitlines():
        m2 = KV_LINE.match(line)
        if m2:
            flat.setdefault(m2.group(1), m2.group(2))
    err(path, "frontmatter", "yaml rejected, flat fallback")
    return flat, front, body, "fallback"


def dig(data, *keys):
    cur = data
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


# ---------------------------------------------------------------- enumeration

def enabled_plugins():
    settings = read_json(SETTINGS, {}) or {}
    return {k for k, v in (settings.get("enabledPlugins") or {}).items() if v}


def plugin_records():
    """One record per enabled plugin, including enabled plugins with zero skills.

    Never walks ~/.claude/plugins directly. That is what pulls in the 678 stale cache
    duplicates and the catalog-only marketplaces (ticket 004).
    """
    installed = (read_json(os.path.join(PLUGINS_DIR, "installed_plugins.json"), {}) or {}).get("plugins", {})
    marketplaces = read_json(os.path.join(PLUGINS_DIR, "known_marketplaces.json"), {}) or {}
    enabled = enabled_plugins()
    out = []
    for key, recs in installed.items():
        if key not in enabled or not recs:
            continue
        rec = recs[0]  # ponytail: first record only. Multiple entries per key are not
                       # present on this machine; revisit if enabledPlugins ever pins a version.
        name, _, marketplace = key.partition("@")
        install_path = rec.get("installPath", "")
        # Manifests live under .claude-plugin/, not at the install root. 004 named the wrong
        # path, which silently sent all 257 plugin entries to the assumed "Eli" author.
        pj = read_json(os.path.join(install_path, ".claude-plugin", "plugin.json"), {}) or {}
        mj = read_json(os.path.join(PLUGINS_DIR, "marketplaces", marketplace,
                                    ".claude-plugin", "marketplace.json"), {}) or {}
        skills = sorted(glob.glob(os.path.join(install_path, ONE_LEVEL)))
        out.append({
            "key": key, "name": name, "marketplace": marketplace,
            "version": rec.get("version"), "install_path": install_path,
            "last_updated": rec.get("lastUpdated"),
            "skill_count": len(skills), "enabled": True,
            "_skill_files": skills,
            "_author": dig(pj, "author", "name") or dig(mj, "owner", "name"),
            "_author_source": "plugin" if dig(pj, "author", "name") else ("marketplace" if dig(mj, "owner", "name") else None),
            "_repository": pj.get("repository") if isinstance(pj.get("repository"), str)
                           else dig(pj, "repository", "url"),
            "_marketplace_source": dig(marketplaces, marketplace, "source", "repo"),
        })
    return sorted(out, key=lambda p: p["key"])


def global_skill_files():
    """Global root, one level, path-prefix exclusions (004 section 5).

    Absent root is not an error state: a teammate running this on a fresh machine has no
    ~/.claude/skills yet, and gets an empty library rather than a traceback (007 amendment).
    """
    if not os.path.isdir(GLOBAL_ROOT):
        err(GLOBAL_ROOT, "global_root", "absent, no personal skills scanned")
        return []
    files = []
    for entry in sorted(os.listdir(GLOBAL_ROOT)):
        if entry.startswith(".") or entry.endswith("-workspace"):
            continue
        f = os.path.join(GLOBAL_ROOT, entry, "SKILL.md")
        if os.path.isfile(f):
            files.append(f)
    return files


def command_vocabulary():
    if not os.path.isdir(COMMANDS_ROOT):
        return []
    return sorted(os.path.splitext(os.path.basename(f))[0]
                  for f in glob.glob(os.path.join(COMMANDS_ROOT, "*.md")))


# ---------------------------------------------------------------- entries

# 011 defaulted the residual author to the machine owner and spelled it "Eli", because that is
# who the machine belonged to. On anyone else's machine that spelling told them their own skills
# were written by someone else, which is the one place the tool asserted a fact it had not
# measured. The owner is now read rather than assumed: git's configured name first, because it is
# a display name a person chose for themselves, then the login name. Absent both, the author stays
# null, which the page already renders as `Unknown` with the ring dashed. No scan error either
# way - a machine with no git identity is a normal machine, not a broken one.
_OWNER = []


def machine_owner():
    """The display name to fall back on when nothing declares an author. Cached: 426 entries."""
    if not _OWNER:
        name = None
        try:
            out = subprocess.run(("git", "config", "user.name"),
                                 capture_output=True, text=True, timeout=10)
            name = out.stdout.strip() if out.returncode == 0 else None
        except (OSError, subprocess.SubprocessError):
            pass
        if not name:
            try:
                name = getpass.getuser()
            except (OSError, KeyError):
                pass
        _OWNER.append(name or None)
    return _OWNER[0]


def build_entry(skill_file, source, plugin=None, lock=None):
    path = os.path.dirname(skill_file)
    name = os.path.basename(path)
    try:
        with open(skill_file, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError as e:
        err(skill_file, "read", e)
        return None

    fm, front, body, status = parse_frontmatter(text, skill_file)
    declared = fm.get("name")
    lock_rec = (lock or {}).get(name) if source == "global" else None

    if source == "plugin":
        entry_id = "%s:%s" % (plugin["name"], name)
    elif source == "repo":
        entry_id = "repo:%s" % name
    else:
        entry_id = name

    version = (dig(fm, "metadata", "version") or fm.get("version")
               or (plugin["version"] if plugin else None))

    author, author_source = None, None
    for candidate, tag in ((dig(fm, "metadata", "author"), "frontmatter"),
                           (plugin["_author"] if plugin else None,
                            plugin["_author_source"] if plugin else "plugin"),
                           ((lock_rec or {}).get("source"), "skill-lock")):
        if candidate:
            author, author_source = candidate, tag
            break
    if not author:
        owner = machine_owner()
        author, author_source = owner, ("assumed" if owner else None)

    updated_at = (lock_rec or {}).get("updatedAt") or (plugin["last_updated"] if plugin else None)

    repo_twin = os.path.join(REPO_ROOT, name, "SKILL.md")
    also_in_repo = source == "global" and os.path.isfile(repo_twin)
    repo_differs = False
    if also_in_repo:
        try:
            with open(repo_twin, encoding="utf-8", errors="replace") as f:
                repo_differs = f.read() != text
        except OSError as e:
            err(repo_twin, "repo_compare", e)

    return {
        "path": path,
        "skill_file": skill_file,
        "id": entry_id,
        "name": name,
        "declared_name": declared if declared and declared != name else None,
        "description": fm.get("description") or "",
        "source": source,
        "plugin": plugin["key"] if plugin else None,
        "marketplace": plugin["marketplace"] if plugin else None,
        "plugin_version": plugin["version"] if plugin else None,
        "version": version,
        "author": author,
        "author_source": author_source,
        "upstream_url": (lock_rec or {}).get("sourceUrl") or (plugin["_repository"] if plugin else None),
        "updated_at": updated_at,
        "is_symlink": os.path.islink(path) or bool(lock_rec),
        "also_in_repo": also_in_repo,
        "repo_differs": repo_differs,
        "model_invocable": not bool(fm.get("disable-model-invocation")),
        "parse_status": status,
        "body_lines": text.count("\n") + 1,
        "has_resources": any(os.path.isdir(os.path.join(path, d))
                             for d in ("references", "scripts", "agents", "assets", "evals")),
        # Sidecar territory. Present and null so the UI never has to test for absence.
        "domain": None, "domain_secondary": None, "kind": None,
        "category_source": "none", "category_status": "uncategorized",
        "orchestration_reason": None, "gloss": None,
        "publishable": False,
        "_front": front, "_body": body,
    }


def collect_entries():
    lock = (read_json(SKILL_LOCK, {}) or {}).get("skills", {})
    entries, roots = [], []

    files = global_skill_files()
    roots.append({"root": GLOBAL_ROOT, "source": "global", "rule": "*/SKILL.md, excluding dotdirs and *-workspace"})
    for f in files:
        e = build_entry(f, "global", lock=lock)
        if e:
            entries.append(e)

    plugins = plugin_records()
    for p in plugins:
        roots.append({"root": p["install_path"], "source": "plugin", "rule": ONE_LEVEL})
        for f in p["_skill_files"]:
            e = build_entry(f, "plugin", plugin=p)
            if e:
                entries.append(e)

    # Repo entries only where the name is absent from global. Global is authoritative (004).
    # The repo root is Eli-specific and optional: it contributes 2 of 426 entries here and
    # exists on no other machine, so it is skipped silently when absent (007 amendment).
    if os.path.isdir(REPO_ROOT):
        known = {e["name"] for e in entries if e["source"] == "global"}
        roots.append({"root": REPO_ROOT, "source": "repo",
                      "rule": "*/SKILL.md, names absent from global only"})
        for f in sorted(glob.glob(os.path.join(REPO_ROOT, "*", "SKILL.md"))):
            if os.path.basename(os.path.dirname(f)) not in known:
                e = build_entry(f, "repo")
                if e:
                    entries.append(e)

    for p in plugins:
        p.pop("_skill_files", None)
    return entries, roots, plugins


# ---------------------------------------------------------------- graph

FENCE = re.compile(r"```.*?```", re.DOTALL)
FOOTER = re.compile(r"^#{1,6}\s*(Dependencies|Related skills?|See also|Next steps?)\b.*?"
                    r"(?=^#{1,6}\s|\Z)", re.DOTALL | re.MULTILINE | re.IGNORECASE)
SECTION = re.compile(r"^(#{1,6})\s*(.*)$", re.MULTILINE)
# A heading carrying a `[placeholder]` is template output the skill instructs the agent to
# write, not document structure. launch-sprint's "## Launch log — [Product name] — [Date]"
# is indistinguishable from a real section otherwise, and it ends the step above it early.
PLACEHOLDER = re.compile(r"\[[^\]]+\]")
CODE_SPAN = re.compile(r"`[^`\n]*`")
# 006 Q12: the old pattern had no left-context guard and no URL awareness, so any path
# segment matched. `https://app.example.com/pricing` scored as a call to `pricing`, and
# "(`/checkout`, `/signup`, `/login`)" as a call to `signup`. Eli's short generic names
# (ads, image, schema, pricing, weekly, signup) collide with ordinary URL vocabulary, so
# the noise landed almost entirely on plugin bodies naming his skills.
SLASH_REF = re.compile(r"(?<![\w/.])/([a-z][a-z0-9-]*(?::[a-z][a-z0-9-]*)?)\b(?![/.])")
SKILL_CALL = re.compile(r"Skill\(\s*(?:skill\s*=\s*)?[\"']?([a-z][a-z0-9:-]*)")
BACKTICK = re.compile(r"`/?([a-z][a-z0-9:-]*)`")
INVOKE_LINE = re.compile(r"\b(invoke|invoking|call|calls|calling|run|runs|running|sequence|sequences|delegate|delegates|hand off|hands off|dispatch|dispatches|step \d|phase \d)\b", re.IGNORECASE)
ORCH_WORD = re.compile(r"orchestrat|sequenc|sub-skill", re.IGNORECASE)


def strip_body(body):
    """Footer-stripping is load-bearing: pm-skills stamps a Dependencies footer on every
    leaf, inflating ~30 leaves to four references each (003). Fenced code excluded too.
    """
    return FOOTER.sub("", FENCE.sub("", body))


def refs_in(text, vocab, self_name):
    """Signals are Skill( calls, /slash references, and gated backtick references.

    Unconditional backtick matching was measured and rejected: it inflates the candidate set
    from 44 to 106 by counting prose mentions. But dropping it outright loses
    pm-orchestrator, a confirmed orchestrator that names every sub-skill as a bare backticked
    word inside Step headings. The gate is 003's own signal list: a backticked vocabulary
    name counts only on a line carrying an invocation verb or a Step/Phase heading.
    """
    found = set()
    # Blank code spans that look like a path or URL before slash matching. A backtick span
    # is the one place a bare `/name` is ambiguous: `/ux-flow` is an invocation, `/checkout`
    # in a list of routes is not. Anything carrying a scheme, a second slash, or a dot is
    # a path, not a skill name.
    slashable = CODE_SPAN.sub(
        lambda m: " " * len(m.group(0))
        if ("://" in m.group(0) or m.group(0).count("/") > 1 or "." in m.group(0))
        else m.group(0), text)
    for rx, haystack in ((SLASH_REF, slashable), (SKILL_CALL, text)):
        for token in rx.findall(haystack):
            bare = token.rpartition(":")[2]
            if token in vocab:
                found.add(token)
            elif bare in vocab:
                found.add(bare)
    for line in text.splitlines():
        if not INVOKE_LINE.search(line):
            continue
        for token in BACKTICK.findall(line):
            bare = token.rpartition(":")[2]
            if token in vocab:
                found.add(token)
            elif bare in vocab:
                found.add(bare)
    # A body naming both `posthog:exploring-llm-costs` and `exploring-llm-costs` means one
    # edge, not two. The qualified form wins; the bare twin is dropped before degree.
    for token in list(found):
        if ":" in token:
            found.discard(token.rpartition(":")[2])
    found.discard(self_name)
    return found


def step_blocks(body, vocab, self_name):
    """Every Step/Phase section, in document order, with the references inside it.

    A section runs to the next heading at the same or a shallower level. Ending it at the
    next heading of any level was measured wrong: launch-sprint's "## Step 6: Comms" ended
    at its own "### Build-in-public post", which is where the /marketing-sprint handoff
    lives, so a real target in a real step was dropped.

    Shared by 003's verdict rule and 012's workflow section, deliberately: one definition of
    what a step is. Verdict-neutral when it landed - 10 orchestrators before and after, and
    no field diffs across the 426.
    """
    marks = [(m.start(), len(m.group(1)), m.group(2)) for m in SECTION.finditer(body)
             if not PLACEHOLDER.search(m.group(2))]
    blocks = []
    for i, (start, level, title) in enumerate(marks):
        if not re.search(r"\b(step|phase)\b", title, re.IGNORECASE):
            continue
        end = next((s for s, lvl, _ in marks[i + 1:] if lvl <= level), len(body))
        blocks.append((title, sorted(refs_in(body[start:end], vocab, self_name))))
    return blocks


def step_section_spread(body, vocab, self_name):
    """How many Step/Phase sections contain a reference. Second half of 003's rule."""
    return sum(1 for _, refs in step_blocks(body, vocab, self_name) if refs)


# Step titles are authored markdown: "Step 2: Current state - run `/ux-flow`",
# "Step 8: Roadmap *(client mode only)*". Stripping the two markers here rather than in the
# page keeps the payload smaller and the page free of a markdown parser it has no dependency for.
TITLE_MARKERS = re.compile(r"[`*]")


def clean_title(title):
    return TITLE_MARKERS.sub("", title).strip()


def build_graph(entries, commands):
    by_name = collections.defaultdict(list)
    for e in entries:
        by_name[e["name"]].append(e)
        by_name[e["id"]].append(e)
    vocab = set(by_name) | set(commands)

    for e in entries:
        stripped = strip_body(e["_body"])
        names = sorted(refs_in(stripped, vocab, e["name"]))
        resolved, unresolved = [], []
        for n in names:
            targets = by_name.get(n) or []
            if targets:
                resolved.extend(t["id"] for t in targets)
            else:
                unresolved.append(n)  # a command, or a name matching nothing on disk
        e["delegates_to"] = names
        e["delegates_to_ids"] = sorted(set(resolved))
        e["delegates_to_unresolved"] = unresolved
        e["orchestration_degree"] = len(names)
        e["orchestration_verdict"] = bool(
            len(names) >= 2 and (ORCH_WORD.search(e["_front"] or "")
                                 or step_section_spread(stripped, vocab, e["name"]) >= 2))
        e["orchestration_class"] = None
        e["orchestration_source"] = "rule"
        # 012: the workflow section. Gated on the verdict so 10 of 426 entries carry it -
        # wider is payload for a surface nothing renders, and prune() cannot drop a non-empty
        # list. Whether a ref is unresolved is a set membership test against
        # delegates_to_unresolved, and targets named outside any step are delegates_to minus
        # the union of these refs. Neither needs its own field.
        e["steps"] = [{"title": clean_title(t), "refs": refs}
                      for t, refs in step_blocks(stripped, vocab, e["name"])] \
            if e["orchestration_verdict"] else []

    # reached_via is the inverse index. 003 found it is the strongest field in the model:
    # it exactly recovers the four skills design-sprint hand-labelled "do not run ad hoc".
    inbound = collections.defaultdict(set)
    for e in entries:
        if e["orchestration_verdict"]:
            for target in e["delegates_to_ids"]:
                inbound[target].add(e["id"])
    for e in entries:
        e["reached_via"] = sorted(inbound.get(e["id"], ()))


# ---------------------------------------------------------------- usage

INJECTION = re.compile(r"skillInjection:\s*(\{.*?\})\s*-->")


def blank_usage():
    return {"tool_calls": 0, "tool_call_errors": 0, "injections": 0,
            "injection_considered": 0, "injection_summary_only": 0,
            "injection_dropped_by_budget": 0, "slash_commands": 0,
            "tool_calls_last_at": None, "injections_last_at": None,
            "slash_commands_last_at": None, "first_seen_at": None,
            "aliases": set()}


def bump(store, raw, field, when, alias=None):
    key = raw.rpartition(":")[2]
    rec = store.setdefault(key, blank_usage())
    rec[field] += 1
    rec["aliases"].add(alias or raw)
    stamp = field + "_last_at" if field + "_last_at" in rec else None
    if when:
        if stamp and (rec[stamp] is None or when > rec[stamp]):
            rec[stamp] = when
        if rec["first_seen_at"] is None or when < rec["first_seen_at"]:
            rec["first_seen_at"] = when


def scan_transcripts(store, vocab):
    """Paths A and B. Substring-prefilter before json.loads: 1.34s full parse versus
    0.42s prefiltered (002). Injection payloads are deduped by (file, line, payload)
    because nested escaping inflates raw counts 2.7x.
    """
    files = glob.glob(TRANSCRIPT_GLOB)
    seen, window = set(), [None, None]
    for path in files:
        try:
            handle = open(path, encoding="utf-8", errors="replace")
        except OSError as e:
            err(path, "transcript_open", e)
            continue
        with handle:
            for lineno, line in enumerate(handle):
                has_call = '"Skill"' in line
                has_inject = "skillInjection" in line
                if not (has_call or has_inject):
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                when = rec.get("timestamp")
                if when:
                    window[0] = min(window[0] or when, when)
                    window[1] = max(window[1] or when, when)
                content = (rec.get("message") or {}).get("content")
                if has_call and isinstance(content, list):
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") == "Skill":
                            raw = (c.get("input") or {}).get("skill")
                            if raw:
                                bump(store, raw, "tool_calls", when, alias=raw)
                if has_inject:
                    for payload in INJECTION.findall(line.replace('\\"', '"')):
                        try:
                            data = json.loads(payload)
                        except ValueError:
                            continue
                        fingerprint = (path, lineno, json.dumps(data, sort_keys=True))
                        if fingerprint in seen:
                            continue
                        seen.add(fingerprint)
                        for field, key in (("injections", "injectedSkills"),
                                           ("injection_considered", "matchedSkills"),
                                           ("injection_summary_only", "summaryOnly"),
                                           ("injection_dropped_by_budget", "droppedByBudget")):
                            for raw in (data.get(key) or []):
                                if raw.rpartition(":")[2] in vocab:
                                    bump(store, raw, field, when, alias=raw)
    return len(files), window


def scan_history(store, vocab):
    """Path C. history.jsonl is the primary source: 167 days, never cleaned. This is what
    makes a defensible never_used possible at all (002).
    """
    window, count = [None, None], 0
    try:
        handle = open(HISTORY, encoding="utf-8", errors="replace")
    except OSError as e:
        err(HISTORY, "history_open", e)
        return 0, window
    with handle:
        for line in handle:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            count += 1
            when = iso(ms=rec["timestamp"]) if rec.get("timestamp") else None
            if when:
                window[0] = min(window[0] or when, when)
                window[1] = max(window[1] or when, when)
            display = (rec.get("display") or "").strip()
            if not display.startswith("/"):
                continue
            raw = display[1:].split()[0] if display[1:].split() else ""
            # Inner join on known names only. Free-text matching is rejected as fatal:
            # all 167 personal names appear as prose in some transcript (002).
            if raw and raw.rpartition(":")[2] in vocab:
                bump(store, raw, "slash_commands", when, alias=raw)
    return count, window


def attach_usage(entries, store, generated_at, transcript_window, history_window):
    by_name = collections.defaultdict(list)
    for e in entries:
        by_name[e["name"]].append(e)
    now = parse_iso(generated_at)

    # A defensible never_used needs history that reaches further back than the transcripts
    # already do. On a machine where history.jsonl is absent, or young enough that it adds
    # nothing beyond the 30-day transcript window, nothing is provably never used and every
    # zero is no_data (002's three-state rule, generalised for other machines by 007).
    history_is_deep = bool(history_window[0]) and (
        transcript_window[0] is None or history_window[0] < transcript_window[0])
    window_start = min([x for x in (transcript_window[0], history_window[0]) if x] or [None])

    for e in entries:
        rec = store.get(e["name"])
        candidates = by_name[e["name"]]
        # source == plugin means the only certain evidence channel is the 30-day transcript
        # window, so silence there proves nothing. ponytail: source is the only implementable
        # reading of 002's "a name a typed slash invocation would have recorded".
        coverage = ("full_history" if e["source"] != "plugin" and history_is_deep
                    else "transcripts_only")
        counts = rec or blank_usage()
        total = counts["tool_calls"] + counts["injections"] + counts["slash_commands"]
        stamps = [counts[k] for k in ("tool_calls_last_at", "injections_last_at",
                                      "slash_commands_last_at") if counts[k]]
        last = max(stamps) if stamps else None
        if total and coverage == "transcripts_only" and counts["slash_commands"]:
            coverage = "full_history"

        state = "used" if total else ("never_used" if coverage == "full_history" else "no_data")
        days = None
        if last and now:
            parsed = parse_iso(last)
            days = (now - parsed).days if parsed else None

        e["usage"] = {
            "state": state,
            "total_count": total if state != "no_data" else None,
            "last_used_at": last,
            "first_seen_at": counts["first_seen_at"],
            "days_since_last_use": days,
            "tool_calls": counts["tool_calls"],
            "tool_calls_last_at": counts["tool_calls_last_at"],
            "tool_call_errors": counts["tool_call_errors"],
            "injections": counts["injections"],
            "injections_last_at": counts["injections_last_at"],
            "injection_considered": counts["injection_considered"],
            "injection_summary_only": counts["injection_summary_only"],
            "injection_dropped_by_budget": counts["injection_dropped_by_budget"],
            "slash_commands": counts["slash_commands"],
            "slash_commands_last_at": counts["slash_commands_last_at"],
            "sources": [tag for tag, field in (("tool_call", "tool_calls"),
                                               ("injection", "injections"),
                                               ("slash_command", "slash_commands"))
                        if counts[field]],
            "evidence_window_start": window_start if coverage == "full_history"
                                     else transcript_window[0],
            "coverage": coverage,
            "orphan": False,
            "name_aliases": sorted(counts["aliases"]),
            # An ambiguous count is written to EVERY candidate and flagged. Suppressing it
            # would report a heavily used skill as unused; splitting it would invent a
            # number. Consequence: never sum usage across entries (005).
            "attribution": "exact" if len(candidates) == 1 else "ambiguous",
            "attribution_candidates": None if len(candidates) == 1 else sorted(c["id"] for c in candidates),
        }


def orphan_usage(entries, store):
    known = {e["name"] for e in entries}
    out = []
    for name, rec in sorted(store.items()):
        if name in known:
            continue
        stamps = [rec[k] for k in ("tool_calls_last_at", "injections_last_at",
                                   "slash_commands_last_at") if rec[k]]
        out.append({
            "raw_name": sorted(rec["aliases"])[0] if rec["aliases"] else name,
            "normalized_name": name,
            "counts": {k: rec[k] for k in ("tool_calls", "injections", "slash_commands")},
            "last_used_at": max(stamps) if stamps else None,
        })
    return out


# ---------------------------------------------------------------- assemble

UI_ENTRY_FIELDS = (
    "id", "name", "description", "source", "plugin", "author", "author_source", "version",
    "updated_at", "skill_file", "upstream_url", "body_lines", "has_resources", "model_invocable",
    "repo_differs", "parse_status", "is_symlink", "orchestration_verdict", "orchestration_degree",
    "delegates_to", "delegates_to_unresolved", "reached_via", "steps",
    "domain", "domain_secondary", "kind", "category_source", "category_status", "gloss",
    "orchestration_class", "orchestration_reason",
    "health_flags", "health_candidate", "health_verdict", "health_source",
    "reach_flags", "reach_verdict", "twin_group",
    "example", "example_from", "example_truncated",
)
UI_USAGE_FIELDS = (
    "state", "total_count", "last_used_at", "days_since_last_use", "sources", "coverage",
    "attribution", "attribution_candidates", "tool_calls", "injections", "slash_commands",
)


def prune(d):
    """Drop empty values from an inlined payload dict.

    At 426 entries the repeated key names and nulls are roughly a third of the page weight:
    every entry carries all 29 fields, but `orchestration_verdict` is set on 10 and
    `delegates_to_unresolved` on 3. Zero and non-empty falsy values are kept, because a
    usage count of 0 is a finding (`never_used`) and not an absence. The page restores the
    few arrays it indexes into; everything else is read with a truthiness or null check.
    """
    return {k: v for k, v in d.items()
            if v is not None and v is not False
            and not (isinstance(v, (str, list, dict)) and len(v) == 0)}


def ui_payload(snapshot):
    """The subset the browser actually renders."""
    return {
        "snapshot_generated_at": snapshot["snapshot_generated_at"],
        "counts": snapshot["counts"],
        "usage_sources": snapshot["usage_sources"],
        "releases": snapshot["releases"],
        "duplicates": snapshot["duplicates"],
        # The first-run state is the only reader: with no entries the page has nothing to
        # show and must say which root came back empty. Costs 2 bytes on a clean scan.
        "scan_errors": snapshot["scan_errors"],
        "entries": [
            prune(dict({k: e[k] for k in UI_ENTRY_FIELDS},
                       usage=prune({k: e["usage"][k] for k in UI_USAGE_FIELDS})))
            for e in snapshot["entries"]
        ],
    }



# ---------------------------------------------------------------- categories

# ---------------------------------------------------------------- health (009)

# A drive letter only at a real left boundary. The first pass matched `[A-Za-z]:[\\/]` and
# flagged 48 of 169, because `s://` matches inside every `https://` URL. Guarded it flags 1,
# which is correct. Same lesson as 006 Q12 and the dead-path rule 009 rejected: guard the left
# context or the whole library matches.
DRIVE = re.compile(r"(?<![\w:/])[A-Za-z]:[\\/]{1,2}(?!/)")
CJK = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")
# 002: the description is the text a model reads to decide whether to trigger. Absent trigger
# phrasing is a proxy for a weak one, not a measurement, which is why it only nominates an
# entry for adjudication and never sets a flag on its own.
TRIGGER = re.compile(r"\buse (this )?(skill )?when\b|\bwhen the user\b|\btrigger", re.I)
THIN_LINES = 20

# Every flag is a statement about the file, not a judgment about the writing. None of them
# means the skill cannot load: the 16 that need frontmatter repair are rejected by PyYAML but
# read correctly by the harness, verified against four of them, so there are no severity tiers
# here on purpose (009).
HEALTH_FLAGS = ("frontmatter_repaired", "name_mismatch", "missing_target", "foreign_marker")


def attach_health(entries):
    """Mechanical defect flags, and the pool for the batched adjudication pass.

    Eli's own skills only. The MAP puts improving plugin skills out of scope, so flagging
    them would be 257 rows of a list nobody can act on (009).
    """
    for e in entries:
        e["health_flags"] = []
        e["health_candidate"] = False
        e["health_verdict"] = None
        e["health_source"] = "none"
        if e["source"] == "plugin":
            continue
        flags = []
        if e["parse_status"] != "ok":
            flags.append("frontmatter_repaired")
        # build_entry only records declared_name when it disagrees with the directory, and the
        # directory is what defines the id (004), so the frontmatter name is the wrong one.
        if e["declared_name"]:
            flags.append("name_mismatch")
        if e["delegates_to_unresolved"]:
            flags.append("missing_target")
        text = (e.get("_front") or "") + (e.get("_body") or "")
        if DRIVE.search(text) or CJK.search(text):
            flags.append("foreign_marker")
        e["health_flags"] = flags
        e["health_candidate"] = ((e["body_lines"] or 0) < THIN_LINES
                                 or not TRIGGER.search(e["description"] or ""))


# ---------------------------------------------------------------- reach (010)

# What a skill can touch. The obvious framing — "what permissions does it request" — is the
# wrong one and the measurement says so: 2 entries of 426 declare `allowed-tools`. A skill's
# real capability is whatever the agent running it is allowed to do, and the file says nothing.
# So the unit here is instructed behaviour: what the body tells an agent to do.
#
# Every flag is a statement about the text, never a verdict. `rm -rf` inside a fenced example
# and `rm -rf` in a step the agent will run look identical to a regex, so the labels say
# "contains" and the panel says to read the file. Tier two — adjudicating what the match
# actually means — is deliberately not built; it needs an LLM pass and the sidecar it would
# write to is gitignored, so it would not survive a move to another machine.
#
# Unlike health flags, these run on all 426 including plugin skills. The action on a flagged
# plugin skill is "stop using it", which is available even though fixing it is not.
REACH = (
    ("declares_tools",    re.compile(r"^allowed-tools:", re.M)),
    ("destructive",       re.compile(r"\brm\s+-[a-z]*[rf]|git\s+push\s+(-f\b|--force(?!-with-lease))"
                                     r"|git\s+reset\s+--hard|\bDROP\s+(TABLE|DATABASE)\b"
                                     r"|\bkillall\b|\bTRUNCATE\s+TABLE\b", re.I)),
    ("network",           re.compile(r"\b(curl|wget)\s|\brequests\.(get|post|put|delete)\("
                                     r"|\burllib\.request\b|\bfetch\(\s*[\"'`]https?://")),
    ("credential_paths",  re.compile(r"~/\.ssh|~/\.aws|~/\.config/gcloud|\bid_rsa\b|[Kk]eychain"
                                     r"|\bcredentials\.json\b|(?<![\w.])\.env(?![\w])")),
    ("mcp_server",        re.compile(r"\bmcp__|\bMCP server\b")),
    ("claude_home",       re.compile(r"~/\.claude|\$HOME/\.claude")),
    ("bundles_scripts",   None),   # filesystem, not text
)

# The four that mean the skill can act outside the file it lives in. The other three are
# context a reader wants once the panel is open, not a reason to mark a row in the list.
REACH_SHARP = ("destructive", "network", "credential_paths", "mcp_server")

SCRIPTABLE = (".py", ".sh", ".js", ".ts", ".rb", ".pl")


def attach_reach(entries):
    for e in entries:
        text = (e.get("_front") or "") + (e.get("_body") or "")
        flags = [name for name, pat in REACH if pat and pat.search(text)]
        scripts = os.path.join(e["path"], "scripts")
        try:
            if os.path.isdir(scripts) and any(f.endswith(SCRIPTABLE) for f in os.listdir(scripts)):
                flags.append("bundles_scripts")
        except OSError as exc:
            err(scripts, "reach_scripts", exc)
        e["reach_flags"] = flags
        # Tier two, filled by the categorize pass (013) when someone runs section 4.
        e["reach_verdict"] = None
        e["reach_source"] = "none"


# ---------------------------------------------------------------- example (014)

# The image half of roadmap idea 9 has no source: nobody is drawing 426 GIFs, and one 200KB
# data URI is a fifth of a payload `prune()` fought 22% to shrink. The file already answers the
# question it was meant to answer. 194 of the 1252 `SKILL.md` files under ~/.claude head a
# section Example, Examples or Usage, which is a literal string and therefore a fact, and needs
# no LLM pass. Headings inside a fence are skipped, because a skill about writing skills quotes
# `## Usage` inside a code block.
ATX = re.compile(r"^(#{1,6})[ \t]+(.*)$")
FENCE_LINE = re.compile(r"^\s*(```|~~~)")
# `Example` anything is an example; `Usage` only counts standing alone. Matching `usage\b` as a
# prefix pulled in "Usage Limits" and "Usage Emails", which are policy sections, not examples.
EXAMPLE_TITLE = re.compile(r"^(examples?\b|usage examples?$|usage$)", re.I)
EXAMPLE_LINES = 18
EXAMPLE_CHARS = 1400


def headings(body):
    """(line index, depth, text) for every ATX heading that is not inside a code fence."""
    out, fence = [], None
    for i, line in enumerate(body.split("\n")):
        opener = FENCE_LINE.match(line)
        if opener:
            fence = None if fence and line.strip().startswith(fence) else (fence or opener.group(1))
            continue
        if fence:
            continue
        m = ATX.match(line)
        if m:
            out.append((i, len(m.group(1)), m.group(2).strip()))
    return out


def attach_examples(entries):
    """The skill's own Example or Usage section, verbatim, capped, when it has one.

    Absent means the file states no example, which is a fact about the file and not a judgment
    about the skill, so the page says which heading it came from and links to the path for the
    rest. Nothing here is inferred and nothing is rewritten.
    """
    for e in entries:
        e["example"], e["example_from"], e["example_truncated"] = None, None, False
        body = e.get("_body") or ""
        heads = headings(body)
        hit = next((n for n, (_, depth, title) in enumerate(heads)
                    if depth >= 2 and EXAMPLE_TITLE.match(title)), None)
        if hit is None:
            continue
        start, depth, title = heads[hit]
        end = next((j for j, d, _ in heads[hit + 1:] if d <= depth), None)
        lines = body.split("\n")
        block = lines[start + 1: end if end is not None else len(lines)]
        while block and not block[0].strip():
            block.pop(0)
        while block and not block[-1].strip():
            block.pop()
        if not block:
            continue
        kept = "\n".join(block[:EXAMPLE_LINES])
        text = kept[:EXAMPLE_CHARS].rstrip()
        e["example"] = text
        e["example_from"] = title
        e["example_truncated"] = len(block) > EXAMPLE_LINES or len(text) < len(kept)


# ---------------------------------------------------------------- duplicates (011)

# Grouping is on the id with any plugin prefix stripped, which is the only signal that
# actually fires here: `vercel:ai-sdk` and `vercel-plugin:ai-sdk` are the same file installed
# twice. Cross-name similarity was measured first and found nothing — 12 byte-identical body
# groups, all of them already same-name — so no fuzzy description matching is built. It can be
# added when a group exists that name matching misses.
#
# The recommendation ranks on evidence the snapshot already holds, and stops at a
# recommendation. Nothing here deletes, edits or merges: decision 1.
# Each label finishes the sentence "Keep <id> — ...", so the page never has to rewrite them.
KEEP_RANK = (
    ("it has more recorded uses", lambda e: e["usage"]["total_count"] or 0),
    ("it was used more recently", lambda e: -(e["usage"]["days_since_last_use"]
                                              if e["usage"]["days_since_last_use"] is not None else 10 ** 6)),
    ("it is yours, not a plugin's", lambda e: e["source"] != "plugin"),
    ("it carries fewer defects",  lambda e: -len(e["health_flags"])),
    ("its frontmatter parses",    lambda e: e["parse_status"] == "ok"),
    ("it bundles resources",      lambda e: e["has_resources"]),
    ("it has a longer body",      lambda e: e["body_lines"] or 0),
)


def attach_duplicates(entries):
    """Group same-named entries, recommend one, return the groups for the snapshot."""
    for e in entries:
        e["twin_group"] = None

    by_name = collections.defaultdict(list)
    for e in entries:
        by_name[e["id"].rsplit(":", 1)[-1]].append(e)

    groups = []
    for key, members in sorted(by_name.items()):
        if len(members) < 2:
            continue
        bodies = {e["id"]: ((e.get("_front") or "") + (e.get("_body") or "")) for e in members}
        # Every rank function returns a number or a bool, and more is better in all of them,
        # so one negation orders the whole tuple. Ties fall through to the id, which keeps the
        # order stable across scans rather than letting sort order decide a recommendation.
        ranked = sorted(members, key=lambda e: (tuple(-int(fn(e)) for _, fn in KEEP_RANK), e["id"]))
        top, rest = ranked[0], ranked[1]
        why = next((label for label, fn in KEEP_RANK if fn(top) != fn(rest)), None)
        for e in members:
            e["twin_group"] = key
        groups.append({
            "key": key,
            "members": [e["id"] for e in ranked],
            "identical": len(set(bodies.values())) == 1,
            "keep": top["id"] if why else None,
            "why": why,
        })
    return groups


# ---------------------------------------------------------------- release history

HERE = os.path.dirname(os.path.abspath(__file__))
US, RS = "\x1f", "\x1e"


def git(*args):
    """Run git in this file's own repo. Returns stdout, or None if git cannot answer.

    Read from this file's repo rather than the working directory: the tool is distributed as
    two files (007 amendment), so a teammate running it from anywhere must still get
    Skill Library's history and not whatever repo they happen to be standing in. Missing git, a
    tarball with no .git, and a non-zero exit all mean no history, never a traceback.
    """
    try:
        out = subprocess.run(("git", "-C", HERE) + args, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as e:
        err(HERE, "git", "%s: %s" % (args[0], e))
        return None
    if out.returncode:
        first = (out.stderr or "").strip().splitlines()[:1]
        err(HERE, "git", "%s: %s" % (args[0], first[0] if first else "exit %d" % out.returncode))
        return None
    return out.stdout


def git_commits(rev_range=None):
    """Short sha, author date and subject for a revision range, newest first."""
    out = git("log", "--format=%h" + US + "%aI" + US + "%s", *( [rev_range] if rev_range else [] ))
    rows = []
    for line in (out or "").splitlines():
        parts = line.split(US)
        if len(parts) == 3:
            rows.append({"sha": parts[0], "date": parts[1], "subject": parts[2]})
    return rows


def git_tags():
    """Annotated tags, oldest first, with their message split into headline and body.

    An annotated tag already is a release note: `git tag -a` takes a subject and a body, git
    stores the date, and the commits between two tags are the release by definition. That is
    why there is no releases file to keep in step — the alternative was a hand-maintained
    JSON mapping shas to prose, which is the same writing plus the bookkeeping. A lightweight
    tag has no message of its own, so git falls back to the tagged commit's subject; it still
    renders, it just reads like a commit rather than a release.
    """
    fmt = US.join(["%(refname:short)", "%(creatordate:iso-strict)", "%(objecttype)",
                   "%(contents:subject)", "%(contents:body)"]) + RS
    out = git("for-each-ref", "refs/tags", "--sort=creatordate", "--format=" + fmt)
    tags = []
    for rec in (out or "").split(RS):
        rec = rec.strip("\n")
        if not rec:
            continue
        parts = rec.split(US)
        if len(parts) == 5:
            tags.append({"tag": parts[0], "date": parts[1], "annotated": parts[2] == "tag",
                         "headline": parts[3].strip(), "description": parts[4].strip()})
    return tags


def release_history():
    """One entry per tag, newest first, plus anything committed since the newest tag.

    Commits after the last tag are grouped as Unreleased rather than dropped, on 008's
    principle that the page shows what it has not yet classified.
    """
    tags = git_tags()
    groups, prev = [], None
    for t in tags:
        commits = git_commits("%s..%s" % (prev, t["tag"]) if prev else t["tag"])
        groups.append(dict(t, commits=commits))
        prev = t["tag"]
    out = [{"tag": g["tag"],
            "headline": g["headline"] or g["tag"],
            "description": g["description"],
            "date_start": (sorted(c["date"] for c in g["commits"]) or [g["date"]])[0],
            "date_end": g["date"],
            "commits": g["commits"]}
           for g in reversed(groups)]
    loose = git_commits("%s..HEAD" % prev) if prev else git_commits()
    if loose:
        dates = sorted(c["date"] for c in loose)
        out.insert(0, {"headline": "Unreleased",
                       "description": "Committed but not yet tagged. `git tag -a` writes the "
                                      "headline and the note; the commits below come with it.",
                       "date_start": dates[0], "date_end": dates[-1],
                       "commits": loose, "unreleased": True})
    return out


SIDECAR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sidecar.json")
OVERRIDES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "overrides.json")

CATEGORY_FIELDS = ("domain", "domain_secondary", "kind")


# Sidecar orchestration classes dropped for lack of a mechanical nomination. An override is
# hand-written and wins by design, so only the `llm` source is ever gated.
SIDECAR_DISCARDS = []


def merge_categories(entries):
    """skills.json, then sidecar.json, then overrides.json. Overrides last (005).

    Plugin skills are assigned by rule and never enter the LLM pass (001): they are
    87% of the library and almost entirely platform reference material.
    """
    sidecar = (read_json(SIDECAR, {}) or {}).get("entries", {})
    overrides = (read_json(OVERRIDES, {}) or {}).get("entries", {})

    for e in entries:
        if e["source"] == "plugin":
            e["domain"] = "Platform"
            e["domain_secondary"] = e["plugin"].split("@")[0] if e["plugin"] else None
            e["kind"] = "Reference"
            e["category_source"] = "rule"

        for src, rec in (("llm", sidecar.get(e["id"])), ("override", overrides.get(e["id"]))):
            if not rec:
                continue
            if any(f in rec for f in CATEGORY_FIELDS):
                for f in CATEGORY_FIELDS:
                    e[f] = rec.get(f)
                e["category_source"] = src
            # 003's architecture is that the scanner nominates and the model adjudicates the
            # nominees. A class on an entry `degree >= 2` never nominated is not an adjudication,
            # it is an unrequested promotion: the model filling section 1 fills its neighbours,
            # which took `adjudicated` from 22 to 57. Discards are counted, not pruned (008).
            if rec.get("orchestration_class"):
                if src == "llm" and e["orchestration_degree"] < 2:
                    SIDECAR_DISCARDS.append(e["id"])
                else:
                    e["orchestration_class"] = rec["orchestration_class"]
                    e["orchestration_reason"] = rec.get("orchestration_reason")
                    e["orchestration_source"] = "adjudicated" if src == "llm" else "override"
            if "publishable" in rec:
                e["publishable"] = rec["publishable"]
            if rec.get("health_verdict"):
                e["health_verdict"] = rec["health_verdict"]
                e["health_source"] = "adjudicated" if src == "llm" else "override"
            if rec.get("reach_verdict"):
                e["reach_verdict"] = rec["reach_verdict"]
                e["reach_source"] = "adjudicated" if src == "llm" else "override"
            if rec.get("gloss"):
                e["gloss"] = rec["gloss"]

        # kind is required, so an entry only counts as assigned once it has one.
        e["category_status"] = "assigned" if e["kind"] else "uncategorized"


# ---------------------------------------------------------------- categorize pass (013)

CATEGORIZE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "categorize.md")

# 013 decision 3: descriptions and computed fields, never bodies. Inlining the core pool's
# bodies is 36,828 lines and the difference between a prompt that fits and one that does not.
# The absolute path is what makes section 4 possible anyway: the adjudicator opens the file.
PROMPT_HEAD = """# Skill Library categorisation pass

Generated by `python3 scan.py --categorize`. Snapshot taken %s.

You are filling in the judgment calls Skill Library's scanner cannot make from the filesystem.
Read the sections below and write `%s`.

## Output

One JSON file. Merge into whatever is already there; never replace it, and never delete a key
you did not write. Orphaned keys are kept on purpose (ticket 008).

```json
{
  "schema_version": 1,
  "entries": {
    "<id>": {
      "domain": "...", "domain_secondary": null, "kind": "...", "gloss": "...",
      "orchestration_class": "...", "orchestration_reason": "...",
      "health_verdict": "...", "reach_verdict": "..."
    }
  }
}
```

Every key is optional. Write only the fields the section you are answering asks for, and only
for the ids that section lists. An id you leave out stays unadjudicated, which is a correct
state and not a failure.

The shape above is the union of every section's fields, not a form to complete. A field written
outside its own section is discarded on the next scan, and `orchestration_class` is the one that
gets volunteered: it belongs to section 2 only, whose ids the scanner nominated mechanically.
Answering it for a section 1 id does not promote that skill, it just gets dropped.

## Rules that apply to every section

- These values are labelled "inferred" everywhere they appear. Do not write one you would not
  defend. Leaving a field out is better than guessing it.
- Never invent a number, a date, or a capability. The page states absent data as unknown.
- One sentence maximum for any `_reason`, `_verdict` or `gloss` field. They render inline in a
  34px row or a panel line, not a paragraph.
- Corrections go in `data/overrides.json`, which is hand-written and wins. Do not edit it here.
"""

SECTION_1 = """## Section 1 — Domain and kind (%d entries)

The two facets the register filters on. Both are currently empty for every entry below, which
is why the Domain control shows 2 of 8 options and the Analysis view has nothing to score.

**`domain`** — one of: %s. Or `null`, which means universal rather than unknown: a skill that
genuinely applies across every domain stays in view under all of them. Roughly one in eight
earns `null`; do not reach for it to avoid deciding.

**`domain_secondary`** — optional, display only, same vocabulary. Use it when a second domain is
genuinely co-equal, not merely adjacent. Most entries should leave it out.

**`kind`** — required, exactly one of: %s. Precedence when two fit: Orchestrator first, then the
one describing what the skill *produces* over what it is *about*.

- **Orchestrator** sequences other skills. **Ritual** is a recurring personal routine.
- **Converter** transforms one artifact into another. **Reviewer** judges something existing.
- **Generator** produces a new artifact. **Thinking tool** structures a decision without
  producing a deliverable. **Reference** is lookup material.

**`gloss`** — a short line for a person scanning 426 rows, under 90 characters, no trailing
period. Descriptions are written to trigger a model, so many open "Use when the user..." which
is useless to a reader. Say what the skill does. Omit `gloss` when the first sentence of the
description is already a good one; the page falls back to it.

### Entries
"""

SECTION_2 = """## Section 2 — Orchestration class (%d entries)

The scanner found these mechanically: each names two or more other skills. Ticket 003 measured
every cheap rule that tries to separate real orchestrators from prose that happens to mention
things, and none clears a stamp-it-unreviewed bar, which is why this is a judgment call.

**`orchestration_class`** — exactly one of `orchestrator`, `router`, `leaf`.

- **orchestrator** runs a sequence: it names skills as steps that happen in order.
- **router** points at one of several skills depending on the situation, without a sequence.
- **leaf** does the work itself and merely mentions other skills. Cross-references in prose,
  a "see also" list, and a footer are all `leaf`.

**`orchestration_reason`** — one sentence naming the evidence. "Runs eight numbered steps, each
handing to a named skill" is useful. "It orchestrates things" is not.

`steps` below is what the scanner read out of the file's own Step and Phase headings, in
document order. An entry with steps that each name a target is almost always an orchestrator.

### Entries
"""

SECTION_3 = """## Section 3 — Health verdict (%d entries)

Ticket 009's tier two. These entries are *nominated*, not flagged: either the body is under 20
lines or the description carries no trigger phrasing. Both are proxies for a weak skill, not
measurements of one, so the honest answer is often that nothing is wrong.

**`health_verdict`** — one sentence, written for someone deciding whether to open the file.
Say what to fix, or say the nomination is a false positive and why. A thin body is fine when
the skill is genuinely small. A description without "use when" is fine when it is still
specific enough for a model to trigger on.

Anything in `health_flags` is already stated as fact on the row and needs no verdict from you.
Do not restate it. Note that `frontmatter_repaired` means untidy, not broken: those files load.

### Entries
"""

SECTION_4 = """## Section 4 — Reach (%d entries) — costly, skip freely

Ticket 010's tier two, and the one section that cannot be answered from this file. Each entry
below matched a pattern that means it *might* act outside its own file. To judge it you have to
open the path and read what the match is actually doing, which is %d files.

Skip this section unless you want it. Sections 1 to 3 are what unblock the register.

**`reach_verdict`** — one sentence, and only these three shapes:

- `no reach` plus why the match was innocent. A `rm -rf` inside a fenced example is innocent.
- `reaches out` plus what leaves the machine or what gets written, in concrete terms.
- `needs a read` when you opened it and still are not sure. This is a real answer.

Never a score and never a number. "Risk 7/10" on a row is the fabricated number `PRODUCT.md`
forbids. The flags themselves already say "contains", and they stay that way.

### Entries
"""


def pool_line(e, fields):
    """One entry, one line, tab-free so the markdown table-less list stays readable."""
    bits = ["- `%s`" % e["id"]]
    for f in fields:
        v = e.get(f)
        if f == "description":
            bits.append("  %s" % " ".join((v or "no description on record").split()))
        elif f == "steps":
            if v:
                bits.append("  steps: %s" % "; ".join(
                    "%s -> %s" % (s["title"], ", ".join(s["refs"]) or "nothing") for s in v))
        elif f == "path":
            bits.append("  path: %s" % e["skill_file"])
        elif v:
            bits.append("  %s: %s" % (f, ", ".join(v) if isinstance(v, list) else v))
    return "\n".join(bits)


def categorize_pools(entries):
    """The four pools, minus anything the sidecar has already answered (013 decision 5)."""
    done = (read_json(SIDECAR, {}) or {}).get("entries", {})

    def unanswered(e, field):
        rec = done.get(e["id"]) or {}
        return not rec.get(field)

    return [
        ("category", [e for e in entries
                      if e["category_status"] == "uncategorized" and unanswered(e, "kind")]),
        ("orchestration", [e for e in entries
                           if e["orchestration_degree"] >= 2
                           and unanswered(e, "orchestration_class")]),
        ("health", [e for e in entries
                    if e["health_candidate"] and unanswered(e, "health_verdict")]),
        ("reach", [e for e in entries
                   if set(e["reach_flags"]) & set(REACH_SHARP)
                   and unanswered(e, "reach_verdict")]),
    ]


def write_categorize(entries, generated_at):
    """Emit data/categorize.md, or say nothing needs answering. Returns the pool sizes.

    The tool prepares the pass; a model outside the tool performs it (013 decision 1). That is
    the only shape that works with no API key on a teammate's machine, and it is decision 3 of
    the MAP applied to the tool's own gap: hand over, never do it silently.
    """
    pools = dict(categorize_pools(entries))
    sizes = {k: len(v) for k, v in pools.items()}
    if not any(sizes.values()):
        return sizes

    parts = [PROMPT_HEAD % (generated_at[:10], os.path.relpath(SIDECAR, HERE))]
    spec = (
        ("category", SECTION_1 % (sizes["category"],
                                  ", ".join("`%s`" % d for d in DOMAINS),
                                  ", ".join("`%s`" % k for k in KINDS)),
         ("description",)),
        ("orchestration", SECTION_2 % sizes["orchestration"],
         ("description", "steps", "delegates_to")),
        ("health", SECTION_3 % sizes["health"],
         ("description", "body_lines", "health_flags", "path")),
        ("reach", SECTION_4 % (sizes["reach"], sizes["reach"]),
         ("description", "reach_flags", "path")),
    )
    for key, head, fields in spec:
        if not pools[key]:
            continue
        parts.append(head + "\n".join(pool_line(e, fields) for e in pools[key]) + "\n")

    os.makedirs(os.path.dirname(CATEGORIZE), exist_ok=True)
    with open(CATEGORIZE, "w") as f:
        f.write("\n".join(parts))
    return sizes


def main():
    global REPO_ROOT
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                  "data", "skills.json"))
    ap.add_argument("--prototype", action="store_true",
                    help="also write prototype-ui.html with the snapshot inlined "
                         "(file:// origins cannot fetch a sibling JSON)")
    ap.add_argument("--repo", default=REPO_ROOT, metavar="PATH",
                    help="a skills checkout outside ~/.claude, scanned one level deep. "
                         "Skipped when absent. Default: %(default)s")
    ap.add_argument("--categorize", action="store_true",
                    help="also write data/categorize.md: the prompt for the judgment calls the "
                         "scanner cannot make. Paste it into an assistant, which writes "
                         "data/sidecar.json, then scan again (ticket 013)")
    args = ap.parse_args()
    REPO_ROOT = os.path.expanduser(args.repo)
    generated_at = iso(when=dt.datetime.now(dt.timezone.utc))

    entries, roots, plugins = collect_entries()
    commands = command_vocabulary()
    build_graph(entries, commands)
    attach_health(entries)
    attach_reach(entries)
    attach_examples(entries)
    merge_categories(entries)

    vocab = {e["name"] for e in entries} | set(commands)
    store = {}
    file_count, t_window = scan_transcripts(store, vocab)
    record_count, h_window = scan_history(store, vocab)
    attach_usage(entries, store, generated_at, t_window, h_window)
    orphans = orphan_usage(entries, store)
    duplicates = attach_duplicates(entries)   # ranks on usage, so it runs after usage lands

    settings = read_json(SETTINGS, {}) or {}
    retention = (settings.get("cleanupPeriodDays"))
    for e in entries:
        for key in ("_front", "_body"):
            e.pop(key, None)

    by_source = collections.Counter(e["source"] for e in entries)
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "snapshot_generated_at": generated_at,
        "scanner_version": SCANNER_VERSION,
        "counts": {
            "entries": len(entries),
            "global": by_source["global"],
            "plugin": by_source["plugin"],
            "repo": by_source["repo"],
            "builtin": by_source["builtin"],
            "uncategorized": sum(1 for e in entries if e["category_status"] == "uncategorized"),
            "flagged": sum(1 for e in entries if e["health_flags"]),
            "health_candidates": sum(1 for e in entries if e["health_candidate"]),
            "reaching": sum(1 for e in entries if e["reach_flags"]),
            "duplicate_groups": len(duplicates),
            "orphan_usage": len(orphans),
        },
        "roots": roots,
        "plugins": plugins,
        "command_vocabulary": commands,
        "usage_sources": {
            "transcripts": {
                "file_count": file_count,
                "window_start": t_window[0], "window_end": t_window[1],
                "retention_days": retention if isinstance(retention, int) else 30,
                "retention_source": "settings" if isinstance(retention, int) else "inferred",
            },
            "history": {
                "window_start": h_window[0], "window_end": h_window[1],
                "record_count": record_count,
            },
            "unrecoverable_paths": ["subagent_start_injection", "session_start_seen_skills"],
        },
        "orphan_usage": orphans,
        "duplicates": duplicates,
        "releases": release_history(),
        "scan_errors": SCAN_ERRORS,
        "entries": entries,
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(snapshot, f, indent=1, sort_keys=False)
        f.write("\n")

    if args.prototype:
        # </script> inside the JSON would close the host tag early. The UI reads only a
        # subset of the schema, so the inlined payload is trimmed: full entries triple the
        # page weight for fields nothing renders.
        payload = json.dumps(ui_payload(snapshot), separators=(",", ":")).replace("</", "<\\/")
        here = os.path.dirname(os.path.abspath(__file__))
        for template in sorted(glob.glob(os.path.join(here, "*.template.html"))):
            target = template.replace(".template.html", ".html")
            try:
                with open(template) as f:
                    html = f.read()
                with open(target, "w") as f:
                    f.write(html.replace("__SNAPSHOT_JSON__", payload))
                print("%s  %.0f KB" % (os.path.basename(target), os.path.getsize(target) / 1024))
            except OSError as e:
                print("%s not written: %s" % (os.path.basename(target), e))

    size = os.path.getsize(args.out)
    states = collections.Counter(e["usage"]["state"] for e in entries)
    print("%s  %d entries (%d global, %d plugin, %d repo)  %.0f KB"
          % (args.out, len(entries), by_source["global"], by_source["plugin"],
             by_source["repo"], size / 1024))
    print("usage: %s" % dict(states))
    print("orchestration candidates (degree>=2): %d, rule verdict true: %d"
          % (sum(1 for e in entries if e["orchestration_degree"] >= 2),
             sum(1 for e in entries if e["orchestration_verdict"])))
    if SIDECAR_DISCARDS:
        print("sidecar: %d orchestration classes dropped, no mechanical nomination (%s)"
              % (len(SIDECAR_DISCARDS), ", ".join(sorted(SIDECAR_DISCARDS)[:3]) + ", ..."))
    print("parse: %s" % dict(collections.Counter(e["parse_status"] for e in entries)))
    print("health: %d flagged %s, %d candidates for adjudication"
          % (sum(1 for e in entries if e["health_flags"]),
             dict(collections.Counter(f for e in entries for f in e["health_flags"])),
             sum(1 for e in entries if e["health_candidate"])))
    print("reach: %d entries flagged %s"
          % (sum(1 for e in entries if e["reach_flags"]),
             dict(collections.Counter(f for e in entries for f in e["reach_flags"]))))
    print("duplicates: %d groups covering %d entries, %d byte-identical"
          % (len(duplicates), sum(len(g["members"]) for g in duplicates),
             sum(1 for g in duplicates if g["identical"])))

    if args.categorize:
        sizes = write_categorize(entries, generated_at)
        if any(sizes.values()):
            print("categorize: %s  ->  %s\n  paste it into an assistant, which writes %s, "
                  "then scan again"
                  % (", ".join("%d %s" % (n, k) for k, n in sizes.items() if n),
                     os.path.relpath(CATEGORIZE, HERE), os.path.relpath(SIDECAR, HERE)))
        else:
            # Nothing to ask means nothing is written. A command that emits an empty prompt is
            # a command that gets pasted anyway (013 decision 6).
            print("categorize: every pool is already answered in %s. Nothing written."
                  % os.path.relpath(SIDECAR, HERE))

    if SCAN_ERRORS:
        print("scan_errors: %d (see snapshot)" % len(SCAN_ERRORS))


if __name__ == "__main__":
    main()
