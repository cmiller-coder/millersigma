#!/usr/bin/env python3
"""Deploy the standalone Barton Margin Tracker workbook (PUT existing or POST new)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from add_margin_page import api, build_margin_elements, header_bg_uri

REPO = Path(__file__).resolve().parents[2]
FOLDER_ID = "dc487f89-30a6-48b7-8de8-e0cce0315e1b"
WORKBOOK_NAME = "Barton Margin Tracker"
META_PATH = REPO / "workbooks/barton/margin-workbook.json"


def assignments_element() -> dict:
    themed = json.loads((REPO / "workbooks/barton/spec-themed.json").read_text())
    for el in themed["document"]["elements"]:
        if el.get("id") == "tbl-assignments":
            tbl = json.loads(json.dumps(el))
            tbl["visibleAsSource"] = True
            return tbl
    raise SystemExit("tbl-assignments not found in spec-themed.json")


def build_document() -> dict:
    tbl = assignments_element()
    margin_els, page_layout = build_margin_elements(header_bg_uri())
    elements = [tbl, *margin_els]
    page_layout = page_layout.replace(
        "</Page>",
        '  <Element elementId="tbl-assignments" gridColumn="1 / 2" gridRow="69 / 70"/>\n</Page>',
    )
    layout = '<?xml version="1.0" encoding="utf-8"?>\n' + page_layout.strip()
    return {
        "schemaVersion": 1,
        "kind": "workbook",
        "pages": [{"id": "page-margin", "name": "Margin Tracker"}],
        "elements": elements,
        "layout": layout,
        "settings": {
            "theme": {
                "overrides": {
                    "colors": {
                        "text": "#41454D",
                        "highlight": "#00A5A2",
                        "success": "#007A78",
                        "warning": "#E1A32D",
                        "danger": "#D64545",
                        "darkMode": "hidden",
                    },
                    "colorOverrides": {
                        "backgroundCanvas": "#EEF4F4",
                        "canvasBackground": "#EEF4F4",
                    },
                    "categoricalScheme": [
                        "#00A5A2", "#007A78", "#1E3A4C", "#5BBFB8",
                        "#2D6B6A", "#7A8E99", "#8FD4D2", "#1A5050",
                    ],
                    "backgroundColor": "#EEF4F4",
                    "elementBackgroundColor": "#FFFFFF",
                    "pageWidth": "large",
                }
            }
        },
    }


def load_meta() -> dict:
    if META_PATH.exists():
        return json.loads(META_PATH.read_text())
    return {}


def save_meta(record: dict) -> None:
    safe = {
        "workbookId": record["workbookId"],
        "workbookUrlId": record.get("workbookUrlId") or _url_id(record.get("url", "")),
        "folderId": record.get("folderId", FOLDER_ID),
    }
    META_PATH.write_text(json.dumps(safe, indent=2) + "\n")


def _url_id(url: str) -> str | None:
    if not url:
        return None
    return url.rstrip("/").split("/")[-1]


def main() -> None:
    doc = build_document()
    meta = load_meta()
    wid = meta.get("workbookId")

    if wid:
        spec = api("GET", f"/v2/workbooks/{wid}/spec")
        payload = {
            "name": spec.get("name", WORKBOOK_NAME),
            "folderId": spec.get("folderId", FOLDER_ID),
            "document": doc,
        }
        out_spec = REPO / "workbooks/barton/spec-margin-standalone.json"
        out_spec.write_text(json.dumps(payload, indent=2))
        api("PUT", f"/v2/workbooks/{wid}/spec", payload)
        print("Updated", WORKBOOK_NAME, wid)
    else:
        payload = {"name": WORKBOOK_NAME, "folderId": FOLDER_ID, "document": doc}
        out_spec = REPO / "workbooks/barton/spec-margin-standalone.json"
        out_spec.write_text(json.dumps(payload, indent=2))
        created = api("POST", "/v2/workbooks/spec", payload)
        wid = created.get("workbookId") or created.get("id")
        if not wid:
            raise SystemExit(f"POST did not return workbookId: {created!r}")
        print("Created", WORKBOOK_NAME, wid)

    wb_meta = api("GET", f"/v2/workbooks/{wid}")
    save_meta({
        "workbookId": wid,
        "url": wb_meta.get("url"),
        "folderId": wb_meta.get("folderId", FOLDER_ID),
    })
    print("workbookUrlId", _url_id(wb_meta.get("url", "")))


if __name__ == "__main__":
    main()
