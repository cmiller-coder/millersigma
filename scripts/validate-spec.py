#!/usr/bin/env python3
"""Pre-POST static validation for a Sigma workbook spec.

The Sigma POST/PUT endpoints accept structurally broken specs and silently
rewrite the layout — most notably, per-page `pages[].layout` fields are
discarded, container children stack into a 1/13-wide single column when not
nested in their `<GridContainer>` in the layout XML, and `format` on columns
returns a misleading "Missing 'kind' field" error.

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
    "no-per-page-layout",
    "elements-placed-in-layout",
    "containers-have-children",
    "control-id-unique",
    "image-source-wrapper",
]


def issues_per_page_layout(spec: dict) -> list[str]:
    issues = []
    for i, p in enumerate(spec.get("pages", [])):
        if p.get("layout"):
            issues.append(
                f"pages[{i}] ({p.get('id')}): has a per-page `layout` field. "
                "Sigma silently discards it — move to the top-level `layout` "
                "string with all <Page> elements as siblings."
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
        return ["no top-level `layout` field — workbook will have an auto-generated layout"]
    placed_ids = {
        el.get("elementId")
        for el in root.iter()
        if el.tag in ("LayoutElement", "GridContainer", "TabbedContainer")
    }
    issues = []
    for pi, p in enumerate(spec.get("pages", [])):
        for el in p.get("elements", []):
            eid = el.get("id")
            if eid and eid not in placed_ids:
                issues.append(
                    f"pages[{pi}].elements ({eid}, kind={el.get('kind')}): "
                    "not placed in the layout XML — will render at the page bottom or not at all."
                )
    return issues


def issues_containers_have_children(spec: dict, root: ET.Element | None) -> list[str]:
    if root is None:
        return []
    container_ids = [
        el.get("id")
        for p in spec.get("pages", [])
        for el in p.get("elements", [])
        if el.get("kind") == "container"
    ]
    issues = []
    for cid in container_ids:
        gc = next((el for el in root.iter("GridContainer") if el.get("elementId") == cid), None)
        if gc is None:
            issues.append(
                f"container element `{cid}`: no matching <GridContainer> in layout XML."
            )
        elif len(list(gc)) == 0:
            issues.append(
                f"container element `{cid}`: <GridContainer> has no nested children. "
                "Children must be nested INSIDE the <GridContainer>, not flat siblings."
            )
    return issues


def issues_image_source_wrapper(spec: dict) -> list[str]:
    """As of 2026-07-30, `image` elements and `backgroundImage` require the url
    wrapped in `source:{kind:"url",url:...}` — a bare top-level `url` field is
    rejected by the API as a masked `Invalid kind: "image"` (or
    `backgroundImage.source: Invalid value: undefined`), verified via a live A/B
    POST against staging. Catch it here instead of via that masked error."""
    issues = []
    for pi, p in enumerate(spec.get("pages", [])):
        for ei, el in enumerate(p.get("elements", [])):
            if el.get("kind") == "image" and "url" in el and "source" not in el:
                issues.append(
                    f"pages[{pi}].elements[{ei}] ({el.get('id')}): `image` element has a "
                    "bare top-level `url` — wrap it as `source:{kind:\"url\",url:...}` "
                    "or the API rejects it as a masked `Invalid kind: \"image\"`."
                )
            bg = el.get("backgroundImage")
            if isinstance(bg, dict) and "url" in bg and "source" not in bg:
                issues.append(
                    f"pages[{pi}].elements[{ei}] ({el.get('id')}): `backgroundImage` has a "
                    "bare `url` — wrap it as `source:{kind:\"url\",url:...}` or the API "
                    "rejects it as `backgroundImage.source: Invalid value: undefined`."
                )
    return issues


def issues_control_id_unique(spec: dict) -> list[str]:
    seen: dict[str, str] = {}
    issues = []
    for p in spec.get("pages", []):
        for el in p.get("elements", []):
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


def main() -> None:
    if len(sys.argv) != 2:
        sys.stderr.write("usage: validate-spec.py <spec.json>\n")
        sys.exit(2)
    with open(sys.argv[1]) as f:
        spec = json.load(f)

    root = _parse_layout(spec.get("layout", ""))

    all_issues: list[tuple[str, str]] = []
    for tag, fn in [
        ("no-per-page-layout",          lambda: issues_per_page_layout(spec)),
        ("elements-placed-in-layout",   lambda: issues_elements_placed(spec, root)),
        ("containers-have-children",    lambda: issues_containers_have_children(spec, root)),
        ("control-id-unique",           lambda: issues_control_id_unique(spec)),
        ("image-source-wrapper",        lambda: issues_image_source_wrapper(spec)),
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
