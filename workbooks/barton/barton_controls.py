"""Fix Barton workbook list controls so dropdowns populate from tbl-assignments."""

TBL = "tbl-assignments"

# element id -> source column on tbl-assignments
LIST_CONTROL_COLUMNS: dict[str, str] = {
    "ctrl-specialty": "col-main-specialty",
    "ctrl-state": "col-worksite-state",
    "ctrl-type": "col-assignment-type",
    "ctrl-status": "col-assignment-status",
    "ctrl-specialty-p2": "col-main-specialty",
    "ctrl-status-p2": "col-assignment-status",
}


def fix_filter_control_sources(doc: dict) -> int:
    """Point list controls at tbl-assignments columns (kind=source, not empty manual)."""
    fixed = 0
    for el in doc.get("elements", []):
        if el.get("kind") != "control" or el.get("controlType") != "list":
            continue
        col_id = LIST_CONTROL_COLUMNS.get(el.get("id", ""))
        if not col_id:
            continue
        want = {
            "kind": "source",
            "source": {"kind": "table", "elementId": TBL},
            "columnId": col_id,
        }
        if el.get("source") == want:
            continue
        el["source"] = want
        el["includeNulls"] = "never"
        fixed += 1

    return fixed
