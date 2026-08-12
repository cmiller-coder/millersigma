#!/usr/bin/env python3
"""Pre-POST static validation for a Sigma workbook spec.

The Sigma POST/PUT endpoints accept structurally broken specs and silently
rewrite the layout — most notably, container children stack into a 1/13-wide
single column when not nested in their `<Container>` in the layout XML.

The checks also catch the legacy spec shapes that the API used to accept and
now rejects (elements nested under `pages[]`, `<GridContainer>`/`<LayoutElement>`
layout tags, `value: {id}` on KPIs, `{id}`-style chart axes). See
`skills/sigma-workbook-conventions/reference/workbook-spec-api.md`.

Run before every POST/PUT:

    python3 scripts/validate-spec.py workbooks/<name>/spec.json

Exits 0 on success, non-zero on any issue (one issue per line on stderr).
"""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET


CHECKS = [
    "document-wrapper",
    "no-per-page-elements",
    "no-per-page-layout",
    "elements-placed-in-layout",
    "containers-have-children",
    "column-format-has-kind",
    "control-id-unique",
    "legacy-element-shapes",
]

# Layout tags that place an element. The first name in each pair is current; the
# second is the legacy name the API now rejects (flagged by legacy-element-shapes).
LEAF_TAGS = ("Element", "LayoutElement")
CONTAINER_TAGS = ("Container", "GridContainer", "TabbedContainer")


def document_of(spec: dict) -> dict:
    """The document body, tolerating a legacy spec with no `document` wrapper."""
    return spec.get("document") or spec


def elements_of(spec: dict) -> list[dict]:
    """Every element, from `document.elements` plus any legacy `pages[].elements`."""
    doc = document_of(spec)
    els = list(doc.get("elements") or [])
    for p in doc.get("pages") or []:
        els.extend(p.get("elements") or [])
    return els


def issues_document_wrapper(spec: dict) -> list[str]:
    doc = spec.get("document")
    if doc is None:
        return [
            "no top-level `document` field — the API rejects a flat spec. Wrap "
            "everything except `name`/`folderId` in `document`, with "
            '`document.kind: "workbook"`.'
        ]
    if doc.get("kind") != "workbook":
        return ['`document.kind` must be "workbook".']
    return []


def issues_per_page_elements(spec: dict) -> list[str]:
    issues = []
    for i, p in enumerate(document_of(spec).get("pages") or []):
        if p.get("elements"):
            issues.append(
                f"pages[{i}] ({p.get('id')}): has an `elements` array. The API "
                "rejects this — move every element to the flat `document.elements` "
                "array and place it via the layout XML."
            )
    return issues


def issues_per_page_layout(spec: dict) -> list[str]:
    issues = []
    for i, p in enumerate(document_of(spec).get("pages") or []):
        if p.get("layout"):
            issues.append(
                f"pages[{i}] ({p.get('id')}): has a per-page `layout` field. "
                "Sigma silently discards it — move to `document.layout` with all "
                "<Page> elements as siblings."
            )
    return issues


def _parse_layout(layout: str) -> ET.Element | None:
    if not layout:
        return None
    # Multi-page layout is multiple <Page> siblings under one <?xml ... ?> decl —
    # not a valid single-root XML doc. Wrap to parse.
    cleaned = re.sub(r"<\?xml[^?]*\?>", "", layout).strip()
    wrapped = f"<root>{cleaned}</root>"
    try:
        return ET.fromstring(wrapped)
    except ET.ParseError as e:
        sys.stderr.write(f"validate-spec: layout XML failed to parse: {e}\n")
        return None


def issues_elements_placed(spec: dict, root: ET.Element | None) -> list[str]:
    if root is None:
        return ["no `document.layout` field — workbook will have an auto-generated layout"]
    placed_ids = {
        el.get("elementId")
        for el in root.iter()
        if el.tag in LEAF_TAGS + CONTAINER_TAGS
    }
    issues = []
    for el in elements_of(spec):
        eid = el.get("id")
        if eid and eid not in placed_ids:
            issues.append(
                f"element `{eid}` (kind={el.get('kind')}): not placed in the layout "
                "XML — will render at the page bottom or not at all."
            )
    return issues


def issues_containers_have_children(spec: dict, root: ET.Element | None) -> list[str]:
    if root is None:
        return []
    container_ids = [
        el.get("id") for el in elements_of(spec) if el.get("kind") == "container"
    ]
    issues = []
    for cid in container_ids:
        node = next(
            (el for el in root.iter()
             if el.tag in CONTAINER_TAGS and el.get("elementId") == cid),
            None,
        )
        if node is None:
            issues.append(
                f"container element `{cid}`: no matching <Container> in layout XML."
            )
        elif len(list(node)) == 0:
            issues.append(
                f"container element `{cid}`: <Container> has no nested children. "
                "Children must be nested INSIDE the <Container>, not flat siblings."
            )
    return issues


def issues_column_format(spec: dict) -> list[str]:
    issues = []
    for el in elements_of(spec):
        for col in el.get("columns") or []:
            fmt = col.get("format")
            if isinstance(fmt, dict) and "kind" not in fmt:
                issues.append(
                    f"element `{el.get('id')}` column `{col.get('id')}`: `format` "
                    'is missing its `kind` field. Use {"kind": "number", '
                    '"formatString": "$.3~s"}.'
                )
    return issues


def issues_control_id_unique(spec: dict) -> list[str]:
    seen: dict[str, str] = {}
    issues = []
    for el in elements_of(spec):
        if el.get("kind") != "control":
            continue
        cid = el.get("controlId")
        if not cid:
            continue
        if cid in seen:
            issues.append(
                f"controlId `{cid}` duplicated on elements {seen[cid]} and {el.get('id')}. "
                "controlId is workbook-wide unique."
            )
        else:
            seen[cid] = el.get("id")
    return issues


def issues_legacy_shapes(spec: dict, layout: str) -> list[str]:
    """Shapes the API used to accept and now rejects with a masked error."""
    issues = []
    for tag in ("GridContainer", "LayoutElement"):
        if f"<{tag}" in (layout or ""):
            issues.append(
                f"layout XML uses <{tag}>. The API now returns a bare 500 for the "
                "legacy tags — use <Container> and <Element>."
            )
    for el in elements_of(spec):
        eid, kind = el.get("id"), el.get("kind")
        value = el.get("value")
        if kind == "kpi-chart" and isinstance(value, dict) and "id" in value:
            issues.append(
                f"element `{eid}`: kpi `value` uses the legacy `{{id}}` shape — "
                'use {"columnId": "<col-id>"}.'
            )
        x, y = el.get("xAxis"), el.get("yAxis")
        if isinstance(x, dict) and "id" in x:
            issues.append(
                f"element `{eid}`: `xAxis` uses the legacy `{{id}}` shape — "
                'use {"columnId": "<col-id>"}.'
            )
        if isinstance(y, list):
            issues.append(
                f"element `{eid}`: `yAxis` is an array — use "
                '{"columnIds": ["<col-id>", ...]}.'
            )
    return issues


def main() -> None:
    if len(sys.argv) != 2:
        sys.stderr.write("usage: validate-spec.py <spec.json>\n")
        sys.exit(2)
    with open(sys.argv[1]) as f:
        spec = json.load(f)

    layout = document_of(spec).get("layout") or ""
    root = _parse_layout(layout)

    all_issues: list[tuple[str, str]] = []
    for tag, fn in [
        ("document-wrapper",            lambda: issues_document_wrapper(spec)),
        ("no-per-page-elements",        lambda: issues_per_page_elements(spec)),
        ("no-per-page-layout",          lambda: issues_per_page_layout(spec)),
        ("elements-placed-in-layout",   lambda: issues_elements_placed(spec, root)),
        ("containers-have-children",    lambda: issues_containers_have_children(spec, root)),
        ("column-format-has-kind",      lambda: issues_column_format(spec)),
        ("control-id-unique",           lambda: issues_control_id_unique(spec)),
        ("legacy-element-shapes",       lambda: issues_legacy_shapes(spec, layout)),
    ]:
        for msg in fn():
            all_issues.append((tag, msg))

    if not all_issues:
        print(f"validate-spec: {sys.argv[1]} — all {len(CHECKS)} checks passed")
        sys.exit(0)

    for tag, msg in all_issues:
        sys.stderr.write(f"[{tag}] {msg}\n")
    sys.stderr.write(f"\nvalidate-spec: {len(all_issues)} issue(s) found in {sys.argv[1]}\n")
    sys.exit(1)


if __name__ == "__main__":
    main()
