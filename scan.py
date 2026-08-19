#!/usr/bin/env python3
"""Wayfinder scanner. Writes data/skills.json.

Implements the scan contract in tickets/005-snapshot-schema.md. Read that first: every
root, precedence rule and null semantic below is decided there, not here.

Never writes to any SKILL.md. Read-only is MAP decision 1.

Usage:  python3 scan.py [--out data/skills.json]
"""

import argparse
import collections
import datetime as dt
import glob
import json
import os
import re
import sys

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required. It is already installed on this machine: python3 -c 'import yaml'")

SCHEMA_VERSION = 1
SCANNER_VERSION = "0.1.0"

HOME = os.path.expanduser("~")
GLOBAL_ROOT = os.path.join(HOME, ".claude", "skills")
COMMANDS_ROOT = os.path.join(HOME, ".claude", "commands")
PLUGINS_DIR = os.path.join(HOME, ".claude", "plugins")
SETTINGS = os.path.join(HOME, ".claude", "settings.json")
SKILL_LOCK = os.path.join(HOME, ".agents", ".skill-lock.json")
HISTORY = os.path.join(HOME, ".claude", "history.jsonl")
TRANSCRIPT_GLOB = os.path.join(HOME, ".claude", "projects", "*", "*.jsonl")
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
    """Global root, one level, path-prefix exclusions (004 section 5)."""
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
        author, author_source = "Eli", "assumed"

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
        "orchestration_reason": None,
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
    known = {e["name"] for e in entries if e["source"] == "global"}
    roots.append({"root": REPO_ROOT, "source": "repo", "rule": "*/SKILL.md, names absent from global only"})
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
SECTION = re.compile(r"^#{1,6}\s*(.*)$", re.MULTILINE)
SLASH_REF = re.compile(r"/([a-z][a-z0-9-]*(?::[a-z][a-z0-9-]*)?)\b")
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
    for rx in (SLASH_REF, SKILL_CALL):
        for token in rx.findall(text):
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


def step_section_spread(body, vocab, self_name):
    """How many Step/Phase sections contain a reference. Second half of 003's rule."""
    hits, marks = 0, [(m.start(), m.group(1)) for m in SECTION.finditer(body)]
    for i, (start, title) in enumerate(marks):
        if not re.search(r"\b(step|phase)\b", title, re.IGNORECASE):
            continue
        end = marks[i + 1][0] if i + 1 < len(marks) else len(body)
        if refs_in(body[start:end], vocab, self_name):
            hits += 1
    return hits


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

    for e in entries:
        rec = store.get(e["name"])
        candidates = by_name[e["name"]]
        # source == plugin means the only certain evidence channel is the 30-day transcript
        # window, so silence there proves nothing. ponytail: source is the only implementable
        # reading of 002's "a name a typed slash invocation would have recorded".
        coverage = "transcripts_only" if e["source"] == "plugin" else "full_history"
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
            "evidence_window_start": min(x for x in (transcript_window[0], history_window[0]) if x)
                                     if coverage == "full_history" else transcript_window[0],
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
    "delegates_to", "delegates_to_unresolved", "reached_via",
    "domain", "domain_secondary", "kind", "category_source", "category_status",
    "orchestration_class", "orchestration_reason",
)
UI_USAGE_FIELDS = (
    "state", "total_count", "last_used_at", "days_since_last_use", "sources", "coverage",
    "attribution", "attribution_candidates", "tool_calls", "injections", "slash_commands",
)


def ui_payload(snapshot):
    """The subset the browser actually renders."""
    return {
        "snapshot_generated_at": snapshot["snapshot_generated_at"],
        "counts": snapshot["counts"],
        "usage_sources": snapshot["usage_sources"],
        "entries": [
            dict({k: e[k] for k in UI_ENTRY_FIELDS},
                 usage={k: e["usage"][k] for k in UI_USAGE_FIELDS})
            for e in snapshot["entries"]
        ],
    }



# ---------------------------------------------------------------- categories

SIDECAR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sidecar.json")
OVERRIDES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "overrides.json")

CATEGORY_FIELDS = ("domain", "domain_secondary", "kind")


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
            if rec.get("orchestration_class"):
                e["orchestration_class"] = rec["orchestration_class"]
                e["orchestration_reason"] = rec.get("orchestration_reason")
                e["orchestration_source"] = "adjudicated" if src == "llm" else "override"
            if "publishable" in rec:
                e["publishable"] = rec["publishable"]

        # kind is required, so an entry only counts as assigned once it has one.
        e["category_status"] = "assigned" if e["kind"] else "uncategorized"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                  "data", "skills.json"))
    ap.add_argument("--prototype", action="store_true",
                    help="also write prototype-ui.html with the snapshot inlined "
                         "(file:// origins cannot fetch a sibling JSON)")
    args = ap.parse_args()
    generated_at = iso(when=dt.datetime.now(dt.timezone.utc))

    entries, roots, plugins = collect_entries()
    commands = command_vocabulary()
    build_graph(entries, commands)
    merge_categories(entries)

    vocab = {e["name"] for e in entries} | set(commands)
    store = {}
    file_count, t_window = scan_transcripts(store, vocab)
    record_count, h_window = scan_history(store, vocab)
    attach_usage(entries, store, generated_at, t_window, h_window)
    orphans = orphan_usage(entries, store)

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
        payload = json.dumps(ui_payload(snapshot)).replace("</", "<\\/")
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
    print("parse: %s" % dict(collections.Counter(e["parse_status"] for e in entries)))
    if SCAN_ERRORS:
        print("scan_errors: %d (see snapshot)" % len(SCAN_ERRORS))


if __name__ == "__main__":
    main()
