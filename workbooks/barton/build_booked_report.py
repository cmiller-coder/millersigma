#!/usr/bin/env python3
"""Pixel-perfect Assignment Booked report (PDF/email) for Barton.

Megh asked for a couple of dashboard views in a scheduled/client-ready layout —
not a combo-chart stand-in for the workbook. This is a Sigma REPORT object
(absolute US-Letter landscape), sourced from the same ASSIGNMENT_PROD table.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_booked_dashboard import (
    A,
    CUR,
    CUR_S,
    FOLDER,
    INT,
    NAVY,
    NUM2,
    PCT,
    SLATE,
    TEAL,
    TEAL_DARK,
    WHITE,
    base_table,
    pie,
    region_map,
    grain_control,
    scope_control,
    summary_kpi,
    weekly_chart,
    window_control,
)
from sigma_api import REPO, try_api

META_PATH = Path(__file__).resolve().parent / "booked-report.json"
REPORT_NAME = "Assignment Booked — Client Report"

PAGE_W, PAGE_H = 1056, 816  # US Letter landscape @ 96dpi
MARGIN = 28
HEADER_H, FOOTER_H = 56, 36


def txt(eid: str, body: str, color: str = SLATE, align: str | None = None) -> dict:
    el = {
        "id": eid,
        "kind": "text",
        "body": body,
        "style": {"color": color, "backgroundColor": "transparent", "padding": "none"},
        "verticalAlign": "middle",
    }
    if align:
        el["align"] = align
    return el


def build_document() -> dict:
    count_formula = f"CountDistinct([{A}/Assignment Number])"
    elements = [
        base_table(),
        scope_control(),
        window_control(),
        grain_control(),
        weekly_chart(
            "chart-booked",
            "Assignment Booked Last 5 Weeks",
            "area-chart",
            "cb-v",
            count_formula,
            INT,
            TEAL,
            trend_line=True,
        ),
        weekly_chart(
            "chart-gm",
            "Assignment Booked GM$ Last 5 Weeks",
            "line-chart",
            "cg-v",
            f"Sum([{A}/GM Dollars])",
            CUR_S,
            TEAL_DARK,
            trend_line=True,
        ),
        region_map(count_formula),
        pie("pie-specialty", "By Specialty", f"[{A}/Main Specialty]"),
        summary_kpi("kpi-total", "Booked Total", count_formula, INT),
        summary_kpi("kpi-avg-gm", "Avg GM", f"Avg([{A}/GM Percent])", PCT),
        summary_kpi("kpi-avg-loa", "Avg LOA", f"Avg([{A}/Assignment LOA])", NUM2),
        summary_kpi("kpi-gm-dollars", "GM Dollars", f"Sum([{A}/GM Dollars])", CUR),
        txt(
            "p1-summary",
            (
                "**{{[Booked Total/Value]}}** assignments booked in the last 5 weeks "
                "with avg GM **{{[Avg GM/Value]}}**, avg LOA {{[Avg LOA/Value]}}, "
                "and GM$ **{{[GM Dollars/Value]}}**."
            ),
            NAVY,
        ),
        txt("h-title", "**Barton Associates — Assignment Booked**", NAVY),
        txt("h-sub", "Last 5 weeks  ·  production assignments", SLATE),
        txt(
            "f-note",
            "Confidential. Point-in-time snapshot for client / RFP use. Source: ASSIGNMENT_PROD.",
            SLATE,
        ),
        {"id": "h-rule", "kind": "divider", "style": {"color": TEAL}},
        {"id": "f-rule", "kind": "divider", "style": {"color": "#D4E8E7"}},
    ]

    # Usable height is the page minus BOTH margins and the two panels; content
    # that runs past it silently spills onto a second page.
    inner_w = PAGE_W - 2 * MARGIN
    inner_h = PAGE_H - 2 * MARGIN - HEADER_H - FOOTER_H
    col_w = (inner_w - 20) // 2
    charts_y, charts_h = 138, 230
    lower_y = charts_y + charts_h + 8
    lower_h = inner_h - lower_y
    assert lower_y + lower_h <= inner_h, "report content overflows to a second page"

    layout = f"""<?xml version="1.0" encoding="utf-8"?>
<Page id="p1">
  <Element elementId="p1-summary" x="{MARGIN}" y="8" width="{inner_w}" height="30"/>
  <Element elementId="kpi-total" x="{MARGIN}" y="70" width="240" height="60"/>
  <Element elementId="kpi-avg-gm" x="{MARGIN + 250}" y="70" width="240" height="60"/>
  <Element elementId="kpi-avg-loa" x="{MARGIN + 500}" y="70" width="240" height="60"/>
  <Element elementId="kpi-gm-dollars" x="{MARGIN + 750}" y="70" width="250" height="60"/>
  <Element elementId="chart-booked" x="{MARGIN}" y="{charts_y}" width="{col_w}" height="{charts_h}"/>
  <Element elementId="chart-gm" x="{MARGIN + col_w + 20}" y="{charts_y}" width="{col_w}" height="{charts_h}"/>
  <Element elementId="chart-state" x="{MARGIN}" y="{lower_y}" width="640" height="{lower_h}"/>
  <Element elementId="pie-specialty" x="{MARGIN + 660}" y="{lower_y}" width="{inner_w - 660}" height="{lower_h}"/>
</Page>
<Page id="pdata">
  <Element elementId="tbl-assignments" x="{MARGIN}" y="0" width="{inner_w}" height="400"/>
  <Element elementId="ctrl-scope" x="{MARGIN}" y="410" width="220" height="30"/>
  <Element elementId="ctrl-window" x="{MARGIN + 230}" y="410" width="220" height="30"/>
  <Element elementId="ctrl-grain" x="{MARGIN + 460}" y="410" width="220" height="30"/>
</Page>
<Panel id="global-header" type="header">
  <Element elementId="h-title" x="{MARGIN}" y="8" width="640" height="28"/>
  <Element elementId="h-sub" x="{MARGIN}" y="32" width="640" height="18"/>
  <Element elementId="h-rule" x="{MARGIN}" y="52" width="{inner_w}" height="2"/>
</Panel>
<Panel id="global-footer" type="footer">
  <Element elementId="f-rule" x="{MARGIN}" y="4" width="{inner_w}" height="2"/>
  <Element elementId="f-note" x="{MARGIN}" y="10" width="{inner_w}" height="22"/>
</Panel>
"""
    return {
        "schemaVersion": 1,
        "kind": "report",
        "pages": [
            {"id": "p1", "name": "Assignment Booked"},
            {"id": "pdata", "name": "Data", "visibility": "hidden"},
        ],
        "elements": elements,
        "panels": [
            {
                "id": "global-header",
                "type": "header",
                "title": "Report header",
                "config": {"height": HEADER_H, "backgroundColor": WHITE},
                "pages": ["p1"],
            },
            {
                "id": "global-footer",
                "type": "footer",
                "title": "Report footer",
                "config": {"height": FOOTER_H, "backgroundColor": WHITE},
                "pages": ["p1"],
            },
        ],
        "config": {"margin": MARGIN, "pageHeight": PAGE_H, "pageWidth": PAGE_W},
        "layout": layout,
    }


def main() -> None:
    doc = build_document()
    payload = {"name": REPORT_NAME, "folderId": FOLDER, "document": doc}
    (Path(__file__).resolve().parent / "spec-booked-report.json").write_text(
        json.dumps(payload, indent=2) + "\n"
    )
    meta = json.loads(META_PATH.read_text()) if META_PATH.exists() else {}
    report_id = meta.get("reportId")
    if report_id:
        status, body = try_api("PUT", f"/v2/reports/{report_id}/spec", payload)
        print("PUT report", status, str(body)[:300] if status >= 400 else report_id)
    else:
        status, created = try_api("POST", "/v2/reports/spec", payload)
        print("POST report", status, str(created)[:400])
        if status < 400 and isinstance(created, dict):
            report_id = created.get("reportId") or created.get("id")
    if status < 400 and report_id:
        META_PATH.write_text(json.dumps({"reportId": report_id, "folderId": FOLDER}, indent=2) + "\n")


if __name__ == "__main__":
    main()
