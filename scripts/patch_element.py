#!/usr/bin/env python3
"""Patch ONE element (or a few) in an existing live workbook spec, without
regenerating the whole workbook.

Why this exists: every prior iteration workflow in this repo GETs the current
spec, rebuilds the ENTIRE thing from a generator script, and POSTs it back --
even for a one-field tweak (a KPI title, a formula, a color). That's the token
cost this tool exists to kill. `GET /v2/workbooks/{id}/spec` + PUT still need
the full spec either way (Sigma has no true partial-PATCH endpoint), but this
script does the merge and the necessary defensive cleanup in code instead of
in a model's context window.

Because PUT re-validates the WHOLE spec, sanitize() runs across the entire
document, not just the element(s) being patched -- six real, recurring
write-blockers this session, none related to what you're actually changing,
but any one of them anywhere in the spec fails the PUT:

  1. CSS var(--colors-X) inline colors (from UI-edited rich text) -- rejected
     on write though they render fine live.
  2. conditionalFormats.columnIds drift -- stale references to columns removed
     by iterative UI editing.
  3. controlId charset violations (e.g. parens from a UI-typed name) --
     controlId must match ^[a-zA-Z0-9_-]{1,64}$.
  4. Actions with an empty effects[] array.
  5. Agent tool steps referencing a UI-only Action Sequence sequenceId that
     doesn't round-trip through GET -- unreconstructable, must be dropped.
  6. Cross-page action effects (e.g. an on-close set-control-value) targeting
     a control declared on a DIFFERENT page than the action lives on.

Each sanitize step is conservative: it only touches what's provably broken
(a dangling reference, an unresolvable id) and reports what it changed. It
will not invent data to replace what it removes -- e.g. it drops an
unreconstructable agent-tool step rather than guessing a replacement.

Usage:
    scripts/api/patch-element.sh <workbook-id> <element-id> '<json-patch>' [element-id2 '<patch2>' ...]

Or directly (spec YAML/JSON on stdin, corrected JSON on stdout):
    cat spec.yaml | python3 scripts/patch_element.py <element-id> '<json-patch>' [...] > out.json

A patch is deep-merged into the matching element: dicts merge recursively,
lists and scalars are replaced outright. Use `null` as a value to delete a key.
Find the element by id anywhere in pages[].elements[] (page-level elements),
including inside a page's own array -- NOT inside agents[] (agents/tools are
patched by patching pages[].elements[] the same way if ever needed, but this
tool's primary target is visual/data elements).
"""
from __future__ import annotations

import json
import re
import sys

try:
    import yaml
except ImportError:
    yaml = None

VALID_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
KNOWN_CSS_VARS = {
    "var(--colors-backgroundNeutralSoft)": "#C7CCE8",
    "var(--colors-fillDanger)": "#D94021",
    "var(--colors-fillPrimary)": "#070B44",
    "var(--colors-textNeutralSofter)": "#A9AFCE",
}


def load_spec(raw: str) -> dict:
    raw_stripped = raw.lstrip()
    if raw_stripped.startswith("{"):
        return json.loads(raw)
    if yaml is None:
        sys.exit("patch_element: input looks like YAML but PyYAML isn't installed "
                 "(`pip install pyyaml`) -- or pass JSON instead.")
    return yaml.safe_load(raw)


def deep_merge(dst: dict, patch: dict) -> dict:
    for k, v in patch.items():
        if v is None:
            dst.pop(k, None)
        elif isinstance(v, dict) and isinstance(dst.get(k), dict):
            deep_merge(dst[k], v)
        else:
            dst[k] = v
    return dst


def find_element(spec: dict, element_id: str):
    for page in spec.get("pages", []):
        for el in page.get("elements", []):
            if el.get("id") == element_id:
                return el, page
    return None, None


# ---------- sanitize passes ----------

def _walk_strings(obj):
    """Yield (container, key_or_index, value) for every string leaf, so callers
    can rewrite in place."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str):
                yield obj, k, v
            else:
                yield from _walk_strings(v)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, str):
                yield obj, i, v
            else:
                yield from _walk_strings(v)


def fix_css_vars(spec: dict) -> list[str]:
    notes = []
    for container, key, val in list(_walk_strings(spec)):
        if "var(--colors-" not in val:
            continue
        new_val = val
        for var, hexcolor in KNOWN_CSS_VARS.items():
            new_val = new_val.replace(var, hexcolor)
        if new_val != val:
            container[key] = new_val
            notes.append(f"fix_css_vars: rewrote a var(--colors-*) reference in place")
        else:
            leftover = re.findall(r"var\(--colors-[A-Za-z0-9]+\)", val)
            if leftover:
                notes.append(
                    f"fix_css_vars: UNRECOGNIZED css var(s) {leftover} -- not in "
                    "KNOWN_CSS_VARS, left as-is (will likely fail PUT; add the "
                    "mapping to KNOWN_CSS_VARS once you know the real hex value)"
                )
    return notes


def fix_conditional_formats_drift(spec: dict) -> list[str]:
    notes = []
    for pi, page in enumerate(spec.get("pages", [])):
        for el in page.get("elements", []):
            cfs = el.get("conditionalFormats")
            if not cfs:
                continue
            valid_ids = {c["id"] for c in (el.get("columns") or []) if "id" in c}
            new_cfs = []
            for cf in cfs:
                before = cf.get("columnIds", [])
                after = [c for c in before if c in valid_ids]
                if len(after) != len(before):
                    dropped = set(before) - set(after)
                    notes.append(
                        f"fix_conditional_formats_drift: element `{el.get('id')}` "
                        f"conditionalFormat dropped stale column id(s) {dropped}"
                    )
                cf["columnIds"] = after
                if after:
                    new_cfs.append(cf)
                else:
                    notes.append(
                        f"fix_conditional_formats_drift: element `{el.get('id')}` "
                        "dropped a whole conditionalFormat (no valid columnIds left)"
                    )
            el["conditionalFormats"] = new_cfs
    return notes


def fix_control_id_charset(spec: dict) -> list[str]:
    notes = []
    bad_ids = {}
    for page in spec.get("pages", []):
        for el in page.get("elements", []):
            cid = el.get("controlId")
            if cid and not VALID_ID_RE.match(cid):
                sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", cid)
                bad_ids[cid] = sanitized
    if not bad_ids:
        return notes
    raw = json.dumps(spec)
    for bad, good in bad_ids.items():
        count = raw.count(bad)
        raw = raw.replace(bad, good)
        notes.append(
            f"fix_control_id_charset: `{bad}` -> `{good}` ({count} occurrence(s) "
            "across controlId field + every bracketed formula reference)"
        )
    spec.clear()
    spec.update(json.loads(raw))
    return notes


def fix_empty_actions(spec: dict) -> list[str]:
    notes = []
    for page in spec.get("pages", []):
        for holder in [page] + page.get("elements", []):
            actions = holder.get("actions")
            if not actions:
                continue
            before = len(actions)
            holder["actions"] = [a for a in actions if a.get("effects")]
            if len(holder["actions"]) != before:
                notes.append(
                    f"fix_empty_actions: dropped {before - len(holder['actions'])} "
                    f"action(s) with no effects on `{holder.get('id', holder.get('name', '<page>'))}`"
                )
    return notes


def fix_unresolvable_agent_sequences(spec: dict) -> list[str]:
    notes = []
    for agent in spec.get("agents", []) or []:
        for tool in agent.get("tools", []) or []:
            steps = tool.get("steps", [])
            before = len(steps)
            tool["steps"] = [s for s in steps if "sequenceId" not in s]
            if len(tool["steps"]) != before:
                notes.append(
                    f"fix_unresolvable_agent_sequences: tool `{tool.get('name')}` "
                    f"on agent `{agent.get('name')}` dropped {before - len(tool['steps'])} "
                    "step(s) referencing a UI-only sequenceId"
                )
        before_tools = len(agent.get("tools", []) or [])
        agent["tools"] = [t for t in (agent.get("tools") or []) if t.get("steps")]
        if len(agent["tools"]) != before_tools:
            notes.append(
                f"fix_unresolvable_agent_sequences: dropped "
                f"{before_tools - len(agent['tools'])} now-empty tool(s) from agent `{agent.get('name')}`"
            )
    return notes


def warn_cross_page_control_refs(spec: dict) -> list[str]:
    """WARN ONLY -- do not auto-remove. A modal invoked from page A commonly sets
    a control declared on page A from an on-click action inside the modal (its own
    page in the spec) -- that's normal and works fine. The one confirmed-broken
    case this session was specifically an `on-close` effect failing with "Control
    not found" at PUT time -- but that's not true of cross-page refs in general
    (verified here: blindly dropping them just deleted a working Create-scenario
    button). If PUT actually rejects one of these with "Control not found: X",
    THAT error names the exact action to fix by hand -- don't guess preemptively."""
    notes = []
    control_page = {}
    for page in spec.get("pages", []):
        for el in page.get("elements", []):
            if el.get("kind") == "control" and el.get("controlId"):
                control_page[el["controlId"]] = page.get("id")
    for page in spec.get("pages", []):
        for el in page.get("elements", []):
            for a in el.get("actions") or []:
                for eff in a.get("effects", []):
                    ctrl = eff.get("control")
                    target_page = control_page.get(ctrl) if ctrl else None
                    if ctrl and target_page not in (None, page.get("id")):
                        notes.append(
                            f"warn_cross_page_control_refs: action `{a.get('id')}` "
                            f"(trigger={a.get('trigger')}) on element `{el.get('id')}` "
                            f"(page `{page.get('id')}`) targets control `{ctrl}` declared on "
                            f"page `{target_page}` -- NOT auto-removed; if PUT rejects with "
                            f"\"Control not found: {ctrl}\", that confirms it's actually broken"
                        )
    return notes


SANITIZERS = [
    fix_css_vars,
    fix_conditional_formats_drift,
    fix_control_id_charset,
    fix_empty_actions,
    fix_unresolvable_agent_sequences,
    warn_cross_page_control_refs,
]


def sanitize(spec: dict) -> list[str]:
    notes = []
    for fn in SANITIZERS:
        notes += fn(spec)
    return notes


def main() -> None:
    args = sys.argv[1:]
    if not args or len(args) % 2 != 0:
        sys.exit(
            "usage: patch_element.py <element-id> '<json-patch>' [<element-id2> '<json-patch2>' ...]\n"
            "  (spec YAML or JSON piped in on stdin, corrected JSON written to stdout)"
        )
    pairs = list(zip(args[0::2], args[1::2]))

    spec = load_spec(sys.stdin.read())

    for element_id, patch_raw in pairs:
        if patch_raw.startswith("@"):
            with open(patch_raw[1:]) as f:
                patch = json.load(f)
        else:
            patch = json.loads(patch_raw)
        el, page = find_element(spec, element_id)
        if el is None:
            sys.exit(f"patch_element: no element with id `{element_id}` found in any page")
        deep_merge(el, patch)
        print(f"patch_element: merged patch into `{element_id}` (page `{page.get('id')}`)", file=sys.stderr)

    notes = sanitize(spec)
    for n in notes:
        print(f"patch_element: {n}", file=sys.stderr)

    json.dump(spec, sys.stdout)


if __name__ == "__main__":
    main()
