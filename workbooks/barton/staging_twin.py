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
from upcoming_page import PAGE_ID as UPCOMING_PAGE_ID

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
    # No "New Assignment" value exists in the sample data, so stand net-new work
    # in with a PRODUCT_TYPE that does occur; a value that never matches leaves
    # the repeat rate pinned at a flat 100%, which proves nothing.
    "col-repeat": f'If([{SRC}/PRODUCT_TYPE] = "Computers", 0, 1)',
    # The sample data ends in Aug 2026, so anchor the window instead of Today().
    "col-weeks-back": (
        'DateDiff("week", DateTrunc("week", [Assignment Created Date]), '
        'DateTrunc("week", Date("2026-08-28")))'
    ),
}

# The upcoming page reads Start Date, which the sample table has no equivalent
# of; shifting the order date forward puts recent rows inside the 90-day window.
UPCOMING_STANDINS = {
    "u-col-an": f"[{SRC}/ORDER_NUMBER]",
    "u-col-main-spec": f"[{SRC}/PRODUCT_FAMILY]",
    "u-col-sub-spec": f"[{SRC}/PRODUCT_LINE]",
    "u-col-asgn-type": f"[{SRC}/PRODUCT_TYPE]",
    "u-col-ae": f"[{SRC}/STORE_NAME]",
    "u-col-recruiter": f"[{SRC}/STORE_CITY]",
    "u-col-state": f"[{SRC}/STORE_STATE]",
    "u-col-loa": f"[{SRC}/QUANTITY]",
    "u-col-bill": f"[{SRC}/PRICE]",
    "u-col-pay": f"[{SRC}/COST]",
    "u-col-start": f'DateAdd("day", 60, [{SRC}/DATE])',
    "u-col-prod": '"Yes"',
    "u-col-start-period": (
        'Switch([UpcomingGrain], '
        f'"Monthly", DateTrunc("month", DateAdd("day", 60, [{SRC}/DATE])), '
        f'DateTrunc("week", DateAdd("day", 60, [{SRC}/DATE])))'
    ),
    "u-col-days-out": f'DateDiff("day", Today(), DateAdd("day", 60, [{SRC}/DATE]))',
}


def twin_document() -> dict:
    doc = json.loads(json.dumps(build_document()))
    standins = {"tbl-assignments": COLUMN_STANDINS, "tbl-upcoming": UPCOMING_STANDINS}
    for element in doc["elements"]:
        table = standins.get(element["id"])
        if table is None:
            continue
        element["source"] = {
            "kind": "warehouse-table",
            "connectionId": CONN,
            "path": TABLE_PATH,
        }
        for column in element["columns"]:
            if column["id"] in table:
                column["formula"] = table[column["id"]]
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
    for el_id in ("chart-booked", "chart-gm", "chart-gmpct", "chart-loa",
                  "chart-repeat", "u-chart-starts", "u-chart-revenue"):
        if not elements.get(el_id, {}).get("trendlines"):
            raise SystemExit(f"{el_id}: trendlines did not survive the round trip")
    if not elements.get("chart-state", {}).get("label"):
        raise SystemExit("chart-state: region labels did not survive the round trip")
    for el_id in ("tbl-detail", "tbl-upcoming-detail"):
        if not any(c.get("link") for c in elements[el_id]["columns"]):
            raise SystemExit(f"{el_id}: link column did not survive the round trip")
    print("round trip ok: trend lines, state labels, link columns")

    for page_id, name in ((PAGE_ID, "booked-dashboard-twin"),
                          (UPCOMING_PAGE_ID, "upcoming-assignments-twin")):
        print("rendered", render_page_png(
            workbook_id, page_id, REPO / f"artifacts/{name}.png"))


if __name__ == "__main__":
    main()
