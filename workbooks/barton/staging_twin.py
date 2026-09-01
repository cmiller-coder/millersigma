#!/usr/bin/env python3
"""Render the booked page against Sigma staging sample data.

The Barton org's API credentials are not available in every environment, and a
spec that only passes `verify` is not proof of anything — element shapes like
trend lines and map labels validate happily and then silently fail to draw. This
rebuilds the same document against a staging warehouse table so the page can be
exported to PNG and looked at.

    SIGMA_BASE_URL=<staging host> python3 workbooks/barton/staging_twin.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_booked_dashboard import PAGE_ID, build_document
from sigma_api import REPO, render_page_png, try_api

FOLDER = os.environ.get("SIGMA_TWIN_FOLDER", "5d84c7c2-ab6c-4208-819b-638bd75452d1")
CONN = os.environ.get("SIGMA_TWIN_CONNECTION", "e0a14c77-3b70-453b-b8a3-00dd6974aebc")
TABLE_PATH = ["EXAMPLES", "PLUGS_ELECTRONICS", "PLUGS_ELECTRONICS_HANDS_ON_LAB_DATA"]
SRC = TABLE_PATH[-1]
META_PATH = Path(__file__).resolve().parent / "staging-twin.json"

# Stand-ins chosen for shape, not meaning: a text dimension for each Barton text
# dimension, a state column for the map, numerics for the rate maths.
COLUMN_STANDINS = {
    "col-an": f"[{SRC}/ORDER_NUMBER]",
    "col-main-spec": f"[{SRC}/PRODUCT_FAMILY]",
    "col-sub-spec": f"[{SRC}/PRODUCT_LINE]",
    "col-asgn-type": f"[{SRC}/PRODUCT_TYPE]",
    "col-provider-type": f"[{SRC}/BRAND]",
    "col-ae": f"[{SRC}/STORE_NAME]",
    "col-ae-entity": f"[{SRC}/STORE_REGION]",
    "col-recruiter": f"[{SRC}/STORE_CITY]",
    "col-state": f"[{SRC}/STORE_STATE]",
    "col-loa": f"[{SRC}/QUANTITY]",
    "col-bill": f"[{SRC}/PRICE]",
    "col-pay": f"[{SRC}/COST]",
    "col-created": f"[{SRC}/DATE]",
    "col-prod": '"Yes"',
    # The sample data ends in Aug 2026, so anchor the window instead of Today().
    "col-weeks-back": (
        'DateDiff("week", DateTrunc("week", [Assignment Created Date]), '
        'DateTrunc("week", Date("2026-08-28")))'
    ),
}


def twin_document() -> dict:
    doc = json.loads(json.dumps(build_document()))
    for element in doc["elements"]:
        if element["id"] != "tbl-assignments":
            continue
        element["source"] = {
            "kind": "warehouse-table",
            "connectionId": CONN,
            "path": TABLE_PATH,
        }
        for column in element["columns"]:
            if column["id"] in COLUMN_STANDINS:
                column["formula"] = COLUMN_STANDINS[column["id"]]
    return doc


def main() -> None:
    payload = {
        "name": "Barton booked page — staging twin",
        "folderId": FOLDER,
        "document": twin_document(),
    }
    meta = json.loads(META_PATH.read_text()) if META_PATH.exists() else {}
    workbook_id = meta.get("workbookId")
    if workbook_id:
        status, body = try_api("PUT", f"/v2/workbooks/{workbook_id}/spec", payload)
    else:
        status, body = try_api("POST", "/v2/workbooks/spec", payload)
        if status < 400:
            workbook_id = body.get("workbookId")
    print("publish", status, workbook_id if status < 400 else body)
    if status >= 400:
        raise SystemExit(1)
    META_PATH.write_text(json.dumps({"workbookId": workbook_id}, indent=2) + "\n")

    # A GET-back is the only way to catch fields Sigma accepts and then drops.
    _, live = try_api("GET", f"/v2/workbooks/{workbook_id}/spec")
    elements = {e["id"]: e for e in (live.get("document") or live)["elements"]}
    for el_id in ("chart-booked", "chart-gm", "chart-gmpct", "chart-loa"):
        if not elements.get(el_id, {}).get("trendlines"):
            raise SystemExit(f"{el_id}: trendlines did not survive the round trip")
    if not elements.get("chart-state", {}).get("label"):
        raise SystemExit("chart-state: region labels did not survive the round trip")
    if not any(c.get("link") for c in elements["tbl-detail"]["columns"]):
        raise SystemExit("tbl-detail: link column did not survive the round trip")
    print("round trip ok: trend lines, state labels, link column")

    shot = render_page_png(
        workbook_id, PAGE_ID, REPO / "artifacts/booked-dashboard-twin.png"
    )
    print("rendered", shot)


if __name__ == "__main__":
    main()
