#!/usr/bin/env python3
"""RuneScape theming for the Grand Exchange Merchanting Desk.

Two commands matter:

    showcase  build/update a fully themed reference workbook
    retheme   apply the same theming to an existing live workbook

`retheme` never touches plugin elements. It fetches the live spec, restyles
only presentation properties on non-plugin elements, and refuses to publish if
any plugin element changed.
"""

from __future__ import annotations

import argparse
import base64
import copy
import json
import os
import pathlib
import urllib.error
import urllib.parse
import urllib.request


HERE = pathlib.Path(__file__).resolve().parent
CONNECTION_ID = os.environ.get(
    "SIGMA_CONNECTION_ID", "e0a14c77-3b70-453b-b8a3-00dd6974aebc"
)
FOLDER_ID = os.environ.get(
    "SIGMA_FOLDER_ID", "5fc0b75e-b736-4389-b7b1-0a265f0db5cc"
)

# The Grand Exchange interface itself: tanned parchment panels, oiled-leather
# banners, bronze rivets, and the amber the game uses for every heading.
#
# Table headers and cells keep a light default surface that no theme key or
# tableStyle key reaches on this host, so the whole palette is built light-on-
# parchment with dark ink. Dark surfaces are used only where the element's own
# text colours are set explicitly (mastheads and KPI tiles).
LEATHER_DARK = "#241F19"
LEATHER = "#332C24"
PARCHMENT_DEEP = "#D4C49E"
PARCHMENT = "#EADCBA"
PARCHMENT_RAISED = "#F3E9CE"
BRONZE = "#7A6338"
GOLD_EDGE = "#A8873F"
GOLD = "#8A6A1E"
GOLD_BRIGHT = "#FFD782"
GOLD_SOFT = "#E8C173"
INK = "#332A1C"
INK_DIM = "#6E6047"
PROFIT = "#1F6B3A"
PROFIT_TINT = "#CBE3C2"
LOSS = "#8E2C22"
LOSS_TINT = "#F0CFC8"
AMBER_TINT = "#F0DFAE"
RUNE_TINT = "#C9DCE4"
RUNE_INK = "#23515F"
# Variants for the dark masthead and KPI tiles, where ink-dark greens read black.
PROFIT_ON_DARK = "#7FD08C"
LOSS_ON_DARK = "#E8785F"

COIN_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
    '<circle cx="24" cy="38" r="20" fill="#E0A828" stroke="#6E4E15" stroke-width="4"/>'
    '<circle cx="40" cy="26" r="22" fill="#FFCE4A" stroke="#6E4E15" stroke-width="4"/>'
    '<circle cx="40" cy="26" r="13" fill="none" stroke="#6E4E15" stroke-width="3"/>'
    "</svg>"
)
COIN_URI = "data:image/svg+xml;base64," + base64.b64encode(COIN_SVG.encode()).decode()

GP = {"kind": "number", "formatString": ",.0f"}
GP_SHORT = {"kind": "number", "formatString": ".3~s"}
PCT1 = {"kind": "number", "formatString": ".1%"}
NUM0 = {"kind": "number", "formatString": ",.0f"}
DATE = {"kind": "datetime", "formatString": "%b %d"}

SCOPE = (
    "Synthetic Grand Exchange records for a theming reference. Prices, volumes "
    "and flips are generated, not live OSRS market data."
)

ITEM_SQL = r"""
SELECT
  item, category, tier, buy_price, sell_price, buy_limit, daily_volume,
  sell_price - buy_price AS gross_margin,
  IFF(sell_price < 50, 0,
      LEAST(FLOOR(sell_price * 0.02), 5000000)) AS ge_tax,
  sell_price - buy_price
    - IFF(sell_price < 50, 0, LEAST(FLOOR(sell_price * 0.02), 5000000))
    AS net_margin,
  (sell_price - buy_price
    - IFF(sell_price < 50, 0, LEAST(FLOOR(sell_price * 0.02), 5000000)))
    / NULLIF(buy_price, 0) AS roi,
  (sell_price - buy_price
    - IFF(sell_price < 50, 0, LEAST(FLOOR(sell_price * 0.02), 5000000)))
    * buy_limit AS limit_profit,
  daily_volume * buy_price AS gp_traded
FROM VALUES
  ('Twisted bow','Weapon','Third age',1204000000,1259000000,8,142),
  ('Scythe of vitur','Weapon','Third age',962000000,1011000000,8,96),
  ('Elysian spirit shield','Shield','Third age',742000000,779000000,8,54),
  ('Ancestral robe top','Armour','Third age',312000000,329000000,8,188),
  ('Dragon claws','Weapon','Dragon',86400000,90100000,8,412),
  ('Twisted ancestral hat','Armour','Third age',54200000,56900000,8,71),
  ('Bandos chestplate','Armour','Rune',19800000,20600000,8,624),
  ('Toxic blowpipe','Weapon','Dragon',4820000,5040000,70,1840),
  ('Abyssal whip','Weapon','Rune',1690000,1762000,70,3120),
  ('Dragon boots','Armour','Dragon',212000,221500,70,5640),
  ('Rune platebody','Armour','Rune',38200,39900,125,18400),
  ('Magic logs','Resource','Bulk',1082,1131,15000,2840000),
  ('Dragon bones','Resource','Bulk',2410,2518,15000,1960000),
  ('Death rune','Resource','Bulk',186,195,25000,9420000),
  ('Zulrah''s scales','Resource','Bulk',142,149,30000,14800000),
  ('Saradomin brew(4)','Consumable','Bulk',10420,10880,8000,412000)
  AS t(item, category, tier, buy_price, sell_price, buy_limit, daily_volume)
""".strip()

OFFER_SQL = r"""
SELECT * FROM VALUES
  (1,'Twisted bow','Buy',2,2,1204000000,'Completed','Ge Slot 1'),
  (2,'Scythe of vitur','Sell',1,1,1011000000,'Completed','Ge Slot 2'),
  (3,'Dragon claws','Buy',8,5,86400000,'Partially filled','Ge Slot 3'),
  (4,'Abyssal whip','Sell',40,12,1762000,'Partially filled','Ge Slot 4'),
  (5,'Bandos chestplate','Buy',4,0,19800000,'Pending','Ge Slot 5'),
  (6,'Magic logs','Buy',15000,15000,1082,'Completed','Ge Slot 6'),
  (7,'Death rune','Sell',25000,9400,195,'Partially filled','Ge Slot 7'),
  (8,'Dragon boots','Buy',70,0,212000,'Pending','Ge Slot 8')
  AS t(slot_no, item, offer_type, quantity, filled, unit_price, status, slot)
""".strip()

PRICE_SQL = r"""
WITH days AS (SELECT SEQ4() AS d FROM TABLE(GENERATOR(ROWCOUNT => 30))),
items AS (
  SELECT column1::STRING AS item, column2::NUMBER AS base, column3::NUMBER AS swing
  FROM VALUES
    ('Twisted bow',1204000000,46000000),
    ('Scythe of vitur',962000000,38000000),
    ('Dragon claws',86400000,4100000),
    ('Abyssal whip',1690000,92000)
),
priced AS (
  SELECT
    DATEADD('day', d - 29, CURRENT_DATE()) AS trade_day,
    i.item,
    i.base + i.swing * SIN((d + LENGTH(i.item)) / 4.0)
      + i.swing * 0.3 * COS(d / 2.0) AS mid_price
  FROM days CROSS JOIN items i
)
-- Items span 1.7M to 1.2B gp, so an absolute axis flattens every line but one.
-- Indexing each series to its own opening price keeps the shapes comparable.
SELECT
  trade_day, item, mid_price,
  mid_price / NULLIF(
    FIRST_VALUE(mid_price) OVER (PARTITION BY item ORDER BY trade_day), 0
  ) * 100 AS price_index
FROM priced
""".strip()

FLIP_SQL = r"""
SELECT * FROM VALUES
  ('2026-09-18','Twisted bow',2,1198000000,1259000000,'Closed'),
  ('2026-09-19','Dragon claws',8,85900000,90100000,'Closed'),
  ('2026-09-20','Abyssal whip',40,1684000,1762000,'Closed'),
  ('2026-09-21','Magic logs',15000,1074,1131,'Closed'),
  ('2026-09-22','Bandos chestplate',4,19750000,20600000,'Open'),
  ('2026-09-23','Zulrah''s scales',30000,140,149,'Open')
  AS t(flip_date, item, quantity, bought_at, sold_at, state)
""".strip()


elements: list[dict] = []


def add(element: dict) -> dict:
    elements.append(element)
    return element


def rune_panel(background: str = PARCHMENT, radius: str = "round") -> dict:
    """The workbook's signature surface: leather fill, bronze rivet border."""
    return {
        "backgroundColor": background,
        "borderColor": BRONZE,
        "borderWidth": 2,
        "borderRadius": radius,
    }


def divider(eid: str, color: str = BRONZE) -> None:
    """A gold rule. Rendered as a thin container because the workbook spec on
    this host rejects the `divider` kind."""
    add({
        "id": eid,
        "kind": "container",
        "style": {"backgroundColor": color, "borderRadius": "square", "padding": "none"},
    })


def label(eid: str, text: str) -> None:
    """Amber section heading, the way OSRS titles every interface.

    Text elements drop `style` on this host, so colour comes from the theme
    text token against the dark canvas rather than a per-element override.
    """
    add({"id": eid, "kind": "text", "body": f"### **{text}**", "verticalAlign": "center"})


def note(eid: str, body: str) -> None:
    add({"id": eid, "kind": "text", "body": body, "verticalAlign": "center"})


def sql_table(eid: str, name: str, sql: str, columns: list[dict]) -> None:
    add({
        "id": eid,
        "kind": "table",
        "name": name,
        "source": {"kind": "sql", "connectionId": CONNECTION_ID, "statement": sql},
        "columns": columns,
    })


def parchment_cells(element: dict) -> None:
    """Lay parchment under every cell.

    Cell backgrounds are not reachable from the theme, so a catch-all format is
    the only lever. It is appended rather than inserted because the first
    matching rule wins: the status and tier rules must outrank it.
    """
    column_ids = [column["id"] for column in element.get("columns", [])]
    if not column_ids:
        return
    element.setdefault("conditionalFormats", []).append({
        "type": "single",
        "columnIds": column_ids,
        "condition": "formula",
        "formula": "True",
        "style": {"backgroundColor": PARCHMENT, "color": INK},
    })


def styled_table(element: dict) -> dict:
    parchment_cells(element)
    element["tableComponents"] = {"summaryBar": "hidden"}
    element["tableStyle"] = {
        "preset": "presentation",
        "cellSpacing": "small",
        "gridLines": "horizontal",
        "banding": "hidden",
    }
    element["style"] = rune_panel()
    return element


def page_shell(idx: int) -> None:
    """Full-page dark backplate.

    The theme's canvas keys verify but are dropped on write, so the only way to
    hold a dark page is to sit every element inside a styled container.
    """
    add({
        "id": f"shell-{idx}",
        "kind": "container",
        "style": {
            "backgroundColor": PARCHMENT_DEEP,
            "borderColor": BRONZE,
            "borderWidth": 2,
            "borderRadius": "round",
        },
    })


def masthead(idx: int, title: str, blurb: str) -> None:
    add({
        "id": f"mast-{idx}",
        "kind": "container",
        "style": {
            "backgroundColor": LEATHER_DARK,
            "borderColor": GOLD_EDGE,
            "borderWidth": 3,
            "borderRadius": "round",
        },
    })
    add({
        "id": f"coin-{idx}",
        "kind": "image",
        "source": {"kind": "url", "url": COIN_URI},
        "style": {"fit": "contain", "align": "center"},
    })
    # Text elements drop `style`, and the theme text colour is ink-dark for the
    # parchment pages, so the banner carries its own colour inline.
    add({
        "id": f"title-{idx}",
        "kind": "text",
        "body": (
            f'# <span style="color:{GOLD_BRIGHT}">**{title}**</span>\n'
            f'<span style="color:{PARCHMENT_DEEP}">{blurb}</span>'
        ),
        "verticalAlign": "center",
    })
    add({
        "id": f"nav-{idx}",
        "kind": "navigation",
        "mode": "manual",
        "showIcons": False,
        "optionStyle": {
            "textColor": GOLD_SOFT,
            "selectedColor": GOLD_BRIGHT,
            "style": "pill",
            "orientation": "horizontal",
        },
        "options": [
            {"label": "Exchange", "destination": {"type": "page", "pageId": "pg-desk"}},
            {"label": "Offers", "destination": {"type": "page", "pageId": "pg-offers"}},
            {"label": "Ledger", "destination": {"type": "page", "pageId": "pg-ledger"}},
            {"label": "Scanner", "destination": {"type": "page", "pageId": "pg-scanner"}},
        ],
    })


def kpi(
    eid: str,
    source: str,
    name: str,
    value: str,
    reference: str,
    fmt: dict,
    background: str = LEATHER,
    reference_label: str = "Reference",
    invert: bool = False,
) -> None:
    add({
        "id": eid,
        "kind": "kpi-chart",
        "source": {"kind": "table", "elementId": source},
        "columns": [
            {"id": f"{eid}-v", "name": name, "formula": value, "format": fmt},
            {"id": f"{eid}-r", "name": reference_label, "formula": reference, "format": fmt},
        ],
        "value": {"columnId": f"{eid}-v", "color": GOLD_BRIGHT, "fontSize": 28},
        "comparisonColumn": {"columnId": f"{eid}-r"},
        "comparison": {
            "display": "delta",
            "colorGood": LOSS_ON_DARK if invert else PROFIT_ON_DARK,
            "colorBad": PROFIT_ON_DARK if invert else LOSS_ON_DARK,
            "fontSize": 12,
        },
        "name": {"text": name, "color": GOLD_SOFT, "fontSize": 13},
        "style": rune_panel(background),
    })


def list_control(eid: str, cid: str, name: str, table: str, column: str) -> None:
    add({
        "id": eid,
        "kind": "control",
        "controlId": cid,
        "name": name,
        "controlType": "list",
        "mode": "include",
        "selectionMode": "multiple",
        "values": [],
        "filters": [{"source": {"kind": "table", "elementId": table}, "columnId": column}],
        "source": {
            "kind": "source",
            "source": {"kind": "table", "elementId": table},
            "columnId": column,
        },
        "style": rune_panel(PARCHMENT_RAISED),
    })


def build_spec() -> dict:
    elements.clear()

    sql_table("src-items", "Item Book", ITEM_SQL, [
        {"id": "i-item", "name": "Item", "formula": "[Custom SQL/item]"},
        {"id": "i-cat", "name": "Category", "formula": "[Custom SQL/category]"},
        {"id": "i-tier", "name": "Tier", "formula": "[Custom SQL/tier]"},
        {"id": "i-buy", "name": "Buy Price", "formula": "[Custom SQL/buy_price]", "format": GP},
        {"id": "i-sell", "name": "Sell Price", "formula": "[Custom SQL/sell_price]", "format": GP},
        {"id": "i-limit", "name": "Buy Limit", "formula": "[Custom SQL/buy_limit]", "format": NUM0},
        {"id": "i-vol", "name": "Daily Volume", "formula": "[Custom SQL/daily_volume]", "format": NUM0},
        {"id": "i-gross", "name": "Gross Margin", "formula": "[Custom SQL/gross_margin]", "format": GP},
        {"id": "i-tax", "name": "GE Tax", "formula": "[Custom SQL/ge_tax]", "format": GP},
        {"id": "i-net", "name": "Net Margin", "formula": "[Custom SQL/net_margin]", "format": GP},
        {"id": "i-roi", "name": "ROI", "formula": "[Custom SQL/roi]", "format": PCT1},
        {"id": "i-limit-profit", "name": "Profit Per Limit", "formula": "[Custom SQL/limit_profit]", "format": GP},
        {"id": "i-traded", "name": "GP Traded Daily", "formula": "[Custom SQL/gp_traded]", "format": GP},
    ])

    sql_table("src-offers", "Offer Book", OFFER_SQL, [
        {"id": "o-slot-no", "name": "Slot No", "formula": "[Custom SQL/slot_no]", "format": NUM0},
        {"id": "o-slot", "name": "Slot", "formula": "[Custom SQL/slot]"},
        {"id": "o-item", "name": "Item", "formula": "[Custom SQL/item]"},
        {"id": "o-type", "name": "Offer Type", "formula": "[Custom SQL/offer_type]"},
        {"id": "o-qty", "name": "Quantity", "formula": "[Custom SQL/quantity]", "format": NUM0},
        {"id": "o-filled", "name": "Filled", "formula": "[Custom SQL/filled]", "format": NUM0},
        {"id": "o-price", "name": "Unit Price", "formula": "[Custom SQL/unit_price]", "format": GP},
        {"id": "o-status", "name": "Status", "formula": "[Custom SQL/status]"},
    ])

    sql_table("src-prices", "Price History", PRICE_SQL, [
        {"id": "h-day", "name": "Trade Day", "formula": "[Custom SQL/trade_day]", "format": DATE},
        {"id": "h-item", "name": "Item", "formula": "[Custom SQL/item]"},
        {"id": "h-price", "name": "Mid Price", "formula": "[Custom SQL/mid_price]", "format": GP},
        {"id": "h-index", "name": "Price Index", "formula": "[Custom SQL/price_index]",
         "format": {"kind": "number", "formatString": ",.1f"}},
    ])

    sql_table("src-flips", "Flip History", FLIP_SQL, [
        {"id": "f-date", "name": "Flip Date", "formula": "[Custom SQL/flip_date]"},
        {"id": "f-item", "name": "Item", "formula": "[Custom SQL/item]"},
        {"id": "f-qty", "name": "Quantity", "formula": "[Custom SQL/quantity]", "format": NUM0},
        {"id": "f-buy", "name": "Bought At", "formula": "[Custom SQL/bought_at]", "format": GP},
        {"id": "f-sell", "name": "Sold At", "formula": "[Custom SQL/sold_at]", "format": GP},
        {"id": "f-state", "name": "State", "formula": "[Custom SQL/state]"},
    ])

    items = "Item Book"
    offers = "Offer Book"
    prices = "Price History"

    # ---------------------------------------------------------------- page 1
    page_shell(1)
    masthead(1, "Grand Exchange Merchanting Desk",
             "Varrock · 8 slots · 4-hour buy limits · 2% exchange tax")
    note("scope-1", SCOPE)
    label("lbl-vitals", "▸ Merchanting Vitals")
    divider("div-1")
    list_control("ctrl-cat", "ItemCategory", "Category", "src-items", "i-cat")
    list_control("ctrl-tier", "ItemTier", "Tier", "src-items", "i-tier")

    kpi("kpi-profit", "src-items", "Profit per limit cycle",
        f"Sum([{items}/Profit Per Limit])",
        f"Sum([{items}/Gross Margin] * [{items}/Buy Limit])",
        GP_SHORT, LEATHER, "Before exchange tax")
    kpi("kpi-tax", "src-items", "Exchange tax due",
        f"Sum([{items}/GE Tax] * [{items}/Buy Limit])",
        f"Sum([{items}/Gross Margin] * [{items}/Buy Limit])",
        GP_SHORT, LEATHER_DARK, "Gross margin", invert=True)
    kpi("kpi-roi", "src-items", "Best ROI on the book",
        f"Max([{items}/ROI])", f"Avg([{items}/ROI])",
        PCT1, LEATHER, "Book average")
    kpi("kpi-volume", "src-items", "GP traded daily",
        f"Sum([{items}/GP Traded Daily])",
        f"Sum([{items}/GP Traded Daily]) * 0.88",
        GP_SHORT, LEATHER_DARK, "Yesterday")

    add({
        "id": "chart-price",
        "kind": "line-chart",
        "name": "30-day price movement — indexed to opening price",
        "source": {"kind": "table", "elementId": "src-prices"},
        "columns": [
            {"id": "p-day", "name": "Day", "formula": f"[{prices}/Trade Day]", "format": DATE},
            {"id": "p-price", "name": "Price Index",
             "formula": f"Avg([{prices}/Price Index])",
             "format": {"kind": "number", "formatString": ",.1f"}},
            {"id": "p-item", "name": "Item", "formula": f"[{prices}/Item]"},
        ],
        "xAxis": {"columnId": "p-day"},
        "yAxis": {"columnIds": ["p-price"]},
        "color": {"by": "category", "column": "p-item",
                  "scheme": [BRONZE, PROFIT, RUNE_INK, "#7B4A86"]},
        "legend": {"position": "top"},
        "style": rune_panel(),
    })
    add({
        "id": "chart-margin",
        "kind": "bar-chart",
        "name": "Profit per buy limit",
        "source": {"kind": "table", "elementId": "src-items"},
        "columns": [
            {"id": "m-item", "name": "Item", "formula": f"[{items}/Item]"},
            {"id": "m-profit", "name": "Profit Per Limit", "formula": f"Sum([{items}/Profit Per Limit])", "format": GP_SHORT},
            {"id": "m-color", "name": "Profit Shade", "formula": f"Sum([{items}/Profit Per Limit])", "format": GP_SHORT},
        ],
        "xAxis": {"columnId": "m-item",
                  "sort": {"by": "m-profit", "aggregation": "sum", "direction": "descending"}},
        "yAxis": {"columnIds": ["m-profit"]},
        "color": {"by": "scale", "column": "m-color", "scheme": [GOLD_EDGE, BRONZE],
                  "domain": {"min": 0, "max": 500000000}},
        "legend": {"visibility": "hidden"},
        "style": rune_panel(),
    })
    note("note-1", ("**Exchange rules in the numbers.** Tax is 2% of the sell price, "
                  "rounded down, capped at 5,000,000 gp, and waived under 50 gp. "
                  "Profit is always shown after tax."))

    # ---------------------------------------------------------------- page 2
    page_shell(2)
    masthead(2, "Offer Book", "Eight slots · fills, partials and pending collections")
    label("lbl-slots", "▸ Slot Status")
    divider("div-2")
    kpi("kpi-slots", "src-offers", "Slots in use",
        f"CountDistinct([{offers}/Slot])", "8", NUM0, LEATHER, "Slots available")
    kpi("kpi-filled", "src-offers", "Offers completed",
        f'CountIf([{offers}/Status] = "Completed")',
        f"CountDistinct([{offers}/Slot No])", NUM0, LEATHER_DARK, "Total offers")
    kpi("kpi-committed", "src-offers", "GP committed",
        f"Sum([{offers}/Unit Price] * [{offers}/Quantity])",
        f"Sum([{offers}/Unit Price] * [{offers}/Filled])",
        GP_SHORT, LEATHER, "GP filled")
    styled_table(add({
        "id": "tbl-offers",
        "kind": "table",
        "name": "Active offers",
        "source": {"kind": "table", "elementId": "src-offers"},
        "columns": [
            {"id": "t-slot", "name": "Slot", "formula": f"[{offers}/Slot]"},
            {"id": "t-item", "name": "Item", "formula": f"[{offers}/Item]"},
            {"id": "t-type", "name": "Offer", "formula": f"[{offers}/Offer Type]"},
            {"id": "t-qty", "name": "Quantity", "formula": f"Sum([{offers}/Quantity])", "format": NUM0},
            {"id": "t-filled", "name": "Filled", "formula": f"Sum([{offers}/Filled])", "format": NUM0},
            {"id": "t-progress", "name": "Progress", "formula": "[Filled] / NullIf([Quantity], 0)", "format": PCT1},
            {"id": "t-price", "name": "Unit Price", "formula": f"Sum([{offers}/Unit Price])", "format": GP},
            {"id": "t-status", "name": "Status", "formula": f"Max([{offers}/Status])"},
        ],
        "groupings": [{"id": "t-group", "groupBy": ["t-slot", "t-item", "t-type"],
                       "calculations": ["t-qty", "t-filled", "t-progress", "t-price", "t-status"]}],
        "conditionalFormats": [
            {"type": "dataBars", "columnIds": ["t-progress"], "scheme": [GOLD_EDGE, BRONZE]},
            {"type": "single", "columnIds": ["t-type"], "condition": "=", "value": "Buy",
             "style": {"backgroundColor": PROFIT_TINT, "color": PROFIT, "bold": True}},
            {"type": "single", "columnIds": ["t-type"], "condition": "=", "value": "Sell",
             "style": {"backgroundColor": LOSS_TINT, "color": LOSS, "bold": True}},
            {"type": "single", "columnIds": ["t-status"], "condition": "=", "value": "Completed",
             "style": {"backgroundColor": PROFIT_TINT, "color": PROFIT, "bold": True}},
            {"type": "single", "columnIds": ["t-status"], "condition": "=", "value": "Partially filled",
             "style": {"backgroundColor": AMBER_TINT, "color": GOLD, "bold": True}},
            {"type": "single", "columnIds": ["t-status"], "condition": "=", "value": "Pending",
             "style": {"backgroundColor": PARCHMENT_RAISED, "color": INK_DIM}},
        ],
    }))
    note("note-2", ("**Collect on completion.** Partially filled offers still hold the "
                  "slot, so the desk reads slot pressure before it reads profit."))

    # ---------------------------------------------------------------- page 3
    page_shell(3)
    masthead(3, "Flip Ledger", "Every completed flip, after exchange tax")
    label("lbl-ledger", "▸ Closed and Open Flips")
    divider("div-3")
    styled_table(add({
        "id": "tbl-flips",
        "kind": "table",
        "name": "Flip ledger",
        "source": {"kind": "table", "elementId": "src-flips"},
        "columns": [
            {"id": "l-date", "name": "Flip Date", "formula": "[Flip History/Flip Date]"},
            {"id": "l-item", "name": "Item", "formula": "[Flip History/Item]"},
            {"id": "l-state", "name": "State", "formula": "[Flip History/State]"},
            {"id": "l-qty", "name": "Quantity", "formula": "Sum([Flip History/Quantity])", "format": NUM0},
            {"id": "l-buy", "name": "Bought At", "formula": "Sum([Flip History/Bought At])", "format": GP},
            {"id": "l-sell", "name": "Sold At", "formula": "Sum([Flip History/Sold At])", "format": GP},
            {"id": "l-tax", "name": "Exchange Tax",
             "formula": "Least(Floor([Sold At] * 0.02), 5000000) * [Quantity]", "format": GP},
            {"id": "l-profit", "name": "Profit After Tax",
             "formula": "([Sold At] - [Bought At]) * [Quantity] - [Exchange Tax]", "format": GP},
        ],
        "groupings": [{"id": "l-group", "groupBy": ["l-date", "l-item", "l-state"],
                       "calculations": ["l-qty", "l-buy", "l-sell", "l-tax", "l-profit"]}],
        "conditionalFormats": [
            {"type": "dataBars", "columnIds": ["l-profit"], "scheme": [GOLD_EDGE, BRONZE]},
            {"type": "single", "columnIds": ["l-state"], "condition": "=", "value": "Closed",
             "style": {"backgroundColor": PROFIT_TINT, "color": PROFIT, "bold": True}},
            {"type": "single", "columnIds": ["l-state"], "condition": "=", "value": "Open",
             "style": {"backgroundColor": AMBER_TINT, "color": GOLD, "bold": True}},
            {"type": "single", "columnIds": ["l-profit"], "condition": "formula",
             "formula": "[Profit After Tax] < 0",
             "style": {"backgroundColor": LOSS_TINT, "color": LOSS, "bold": True}},
        ],
    }))
    note("note-3", ("**Tax is charged on the sell side only.** A flip that looks green "
                  "on raw margin can close red once the exchange takes its cut."))

    # ---------------------------------------------------------------- page 4
    page_shell(4)
    masthead(4, "Margin Scanner", "Rank the book by what a full buy limit is worth")
    label("lbl-scan", "▸ Ranked Item Book")
    divider("div-4")
    styled_table(add({
        "id": "tbl-scanner",
        "kind": "table",
        "name": "Margin scanner",
        "source": {"kind": "table", "elementId": "src-items"},
        "columns": [
            {"id": "s-item", "name": "Item", "formula": f"[{items}/Item]"},
            {"id": "s-tier", "name": "Tier", "formula": f"[{items}/Tier]"},
            {"id": "s-buy", "name": "Buy", "formula": f"Sum([{items}/Buy Price])", "format": GP},
            {"id": "s-sell", "name": "Sell", "formula": f"Sum([{items}/Sell Price])", "format": GP},
            {"id": "s-gross", "name": "Gross Margin", "formula": f"Sum([{items}/Gross Margin])", "format": GP},
            {"id": "s-tax", "name": "GE Tax", "formula": f"Sum([{items}/GE Tax])", "format": GP},
            {"id": "s-net", "name": "Net Margin", "formula": f"Sum([{items}/Net Margin])", "format": GP},
            {"id": "s-roi", "name": "ROI", "formula": f"Avg([{items}/ROI])", "format": PCT1},
            {"id": "s-limit", "name": "Buy Limit", "formula": f"Sum([{items}/Buy Limit])", "format": NUM0},
            {"id": "s-profit", "name": "Profit Per Limit", "formula": f"Sum([{items}/Profit Per Limit])", "format": GP},
        ],
        "groupings": [{"id": "s-group", "groupBy": ["s-item", "s-tier"],
                       "calculations": ["s-buy", "s-sell", "s-gross", "s-tax", "s-net",
                                        "s-roi", "s-limit", "s-profit"]}],
        "conditionalFormats": [
            {"type": "dataBars", "columnIds": ["s-profit"], "scheme": [GOLD_EDGE, BRONZE]},
            {"type": "single", "columnIds": ["s-tier"], "condition": "=", "value": "Third age",
             "style": {"backgroundColor": AMBER_TINT, "color": GOLD, "bold": True}},
            {"type": "single", "columnIds": ["s-tier"], "condition": "=", "value": "Dragon",
             "style": {"backgroundColor": LOSS_TINT, "color": LOSS, "bold": True}},
            {"type": "single", "columnIds": ["s-tier"], "condition": "=", "value": "Rune",
             "style": {"backgroundColor": RUNE_TINT, "color": RUNE_INK, "bold": True}},
            {"type": "single", "columnIds": ["s-roi"], "condition": ">", "value": 0.04,
             "style": {"backgroundColor": PROFIT_TINT, "color": PROFIT, "bold": True}},
            {"type": "single", "columnIds": ["s-roi"], "condition": "<", "value": 0.02,
             "style": {"backgroundColor": PARCHMENT_RAISED, "color": INK_DIM}},
        ],
    }))
    note("note-4", ("**Buy limit is the real constraint.** A 4% margin on an item you "
                  "can only buy 8 of loses to a 1% margin you can buy 15,000 of."))

    layout = """<?xml version="1.0" encoding="utf-8"?>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-desk">
  <Container elementId="shell-1" type="grid" gridColumn="1 / 25" gridRow="1 / 44" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Container elementId="mast-1" type="grid" gridColumn="1 / 25" gridRow="1 / 7" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
      <Element elementId="coin-1" gridColumn="1 / 4" gridRow="1 / 7"/>
      <Element elementId="title-1" gridColumn="4 / 16" gridRow="1 / 7"/>
      <Element elementId="nav-1" gridColumn="16 / 25" gridRow="2 / 7"/>
    </Container>
    <Element elementId="scope-1" gridColumn="1 / 25" gridRow="7 / 9"/>
    <Element elementId="lbl-vitals" gridColumn="1 / 13" gridRow="9 / 11"/>
    <Element elementId="div-1" gridColumn="1 / 25" gridRow="11 / 12"/>
    <Element elementId="ctrl-cat" gridColumn="1 / 13" gridRow="12 / 15"/>
    <Element elementId="ctrl-tier" gridColumn="13 / 25" gridRow="12 / 15"/>
    <Element elementId="kpi-profit" gridColumn="1 / 7" gridRow="15 / 23"/>
    <Element elementId="kpi-tax" gridColumn="7 / 13" gridRow="15 / 23"/>
    <Element elementId="kpi-roi" gridColumn="13 / 19" gridRow="15 / 23"/>
    <Element elementId="kpi-volume" gridColumn="19 / 25" gridRow="15 / 23"/>
    <Element elementId="chart-price" gridColumn="1 / 15" gridRow="23 / 39"/>
    <Element elementId="chart-margin" gridColumn="15 / 25" gridRow="23 / 39"/>
    <Element elementId="note-1" gridColumn="1 / 25" gridRow="39 / 42"/>
  </Container>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-offers">
  <Container elementId="shell-2" type="grid" gridColumn="1 / 25" gridRow="1 / 43" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Container elementId="mast-2" type="grid" gridColumn="1 / 25" gridRow="1 / 7" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
      <Element elementId="coin-2" gridColumn="1 / 4" gridRow="1 / 7"/>
      <Element elementId="title-2" gridColumn="4 / 16" gridRow="1 / 7"/>
      <Element elementId="nav-2" gridColumn="16 / 25" gridRow="2 / 7"/>
    </Container>
    <Element elementId="lbl-slots" gridColumn="1 / 13" gridRow="7 / 9"/>
    <Element elementId="div-2" gridColumn="1 / 25" gridRow="9 / 10"/>
    <Element elementId="kpi-slots" gridColumn="1 / 9" gridRow="10 / 18"/>
    <Element elementId="kpi-filled" gridColumn="9 / 17" gridRow="10 / 18"/>
    <Element elementId="kpi-committed" gridColumn="17 / 25" gridRow="10 / 18"/>
    <Element elementId="tbl-offers" gridColumn="1 / 25" gridRow="18 / 38"/>
    <Element elementId="note-2" gridColumn="1 / 25" gridRow="38 / 41"/>
  </Container>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-ledger">
  <Container elementId="shell-3" type="grid" gridColumn="1 / 25" gridRow="1 / 35" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Container elementId="mast-3" type="grid" gridColumn="1 / 25" gridRow="1 / 7" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
      <Element elementId="coin-3" gridColumn="1 / 4" gridRow="1 / 7"/>
      <Element elementId="title-3" gridColumn="4 / 16" gridRow="1 / 7"/>
      <Element elementId="nav-3" gridColumn="16 / 25" gridRow="2 / 7"/>
    </Container>
    <Element elementId="lbl-ledger" gridColumn="1 / 13" gridRow="7 / 9"/>
    <Element elementId="div-3" gridColumn="1 / 25" gridRow="9 / 10"/>
    <Element elementId="tbl-flips" gridColumn="1 / 25" gridRow="10 / 30"/>
    <Element elementId="note-3" gridColumn="1 / 25" gridRow="30 / 33"/>
  </Container>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-scanner">
  <Container elementId="shell-4" type="grid" gridColumn="1 / 25" gridRow="1 / 39" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Container elementId="mast-4" type="grid" gridColumn="1 / 25" gridRow="1 / 7" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
      <Element elementId="coin-4" gridColumn="1 / 4" gridRow="1 / 7"/>
      <Element elementId="title-4" gridColumn="4 / 16" gridRow="1 / 7"/>
      <Element elementId="nav-4" gridColumn="16 / 25" gridRow="2 / 7"/>
    </Container>
    <Element elementId="lbl-scan" gridColumn="1 / 13" gridRow="7 / 9"/>
    <Element elementId="div-4" gridColumn="1 / 25" gridRow="9 / 10"/>
    <Element elementId="tbl-scanner" gridColumn="1 / 25" gridRow="10 / 34"/>
    <Element elementId="note-4" gridColumn="1 / 25" gridRow="34 / 37"/>
  </Container>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-data">
  <Element elementId="src-items" gridColumn="1 / 13" gridRow="1 / 18"/>
  <Element elementId="src-offers" gridColumn="13 / 25" gridRow="1 / 18"/>
  <Element elementId="src-prices" gridColumn="1 / 13" gridRow="18 / 34"/>
  <Element elementId="src-flips" gridColumn="13 / 25" gridRow="18 / 34"/>
</Page>
"""

    return {
        "name": "Grand Exchange Merchanting Desk",
        "folderId": FOLDER_ID,
        "document": {
            "schemaVersion": 1,
            "kind": "workbook",
            "elements": elements,
            "pages": [
                {"id": "pg-desk", "name": "Exchange"},
                {"id": "pg-offers", "name": "Offers"},
                {"id": "pg-ledger", "name": "Ledger"},
                {"id": "pg-scanner", "name": "Scanner"},
                {"id": "pg-data", "name": "Data", "visibility": "hidden"},
            ],
            "layout": layout,
            "settings": {
                "navigation": {"pageHeader": "enabled"},
                "theme": {"overrides": THEME_OVERRIDES},
            },
        },
    }


THEME_OVERRIDES = {
    "colors": {
        "text": INK,
        "highlight": GOLD,
        "success": PROFIT,
        "warning": GOLD,
        "danger": LOSS,
        "darkMode": "hidden",
    },
    # `backgroundColor` / `elementBackgroundColor` are accepted but silently
    # dropped. These two are the keys that actually paint the page.
    "canvasBackground": PARCHMENT_DEEP,
    "backgroundCanvas": PARCHMENT,
    "borderRadius": "round",
    "categoricalScheme": [
        BRONZE, PROFIT, RUNE_INK, "#7B4A86", LOSS, GOLD_EDGE, INK_DIM, "#456B8C",
    ],
    "space": {"unit": "small", "showElementPadding": "shown"},
}


# --------------------------------------------------------------- retheming


PRESENTATION_KEYS = {"style", "tableStyle", "optionStyle", "value", "name", "comparison"}


def iter_elements(node):
    """Yield every element, including those nested inside containers/pages."""
    if isinstance(node, dict):
        if node.get("kind") and node.get("id"):
            yield node
        for key, value in node.items():
            if key in ("elements", "pages", "overlays", "children"):
                yield from iter_elements(value)
    elif isinstance(node, list):
        for item in node:
            yield from iter_elements(item)


def restyle_element(element: dict) -> bool:
    """Apply the RuneScape surface to one non-plugin element."""
    kind = element.get("kind")
    if kind == "plugin":
        return False

    changed = False
    if kind in ("container", "table", "input-table", "pivot-table", "control",
                "bar-chart", "line-chart", "area-chart", "combo-chart",
                "donut-chart", "scatter-chart", "region-map"):
        element["style"] = rune_panel()
        changed = True
    elif kind == "kpi-chart":
        element["style"] = rune_panel(LEATHER)
        element.setdefault("value", {})["color"] = GOLD_BRIGHT
        element.setdefault("name", {})["color"] = GOLD_SOFT
        changed = True
    elif kind == "divider":
        element["style"] = {"color": BRONZE, "width": 2, "strokeStyle": "solid"}
        changed = True
    elif kind == "navigation":
        element["optionStyle"] = {
            "textColor": GOLD_SOFT,
            "selectedColor": GOLD_BRIGHT,
            "style": "pill",
            "orientation": "horizontal",
        }
        changed = True

    if kind in ("table", "input-table"):
        parchment_cells(element)
        element["tableStyle"] = {
            "preset": "presentation",
            "cellSpacing": "small",
            "gridLines": "horizontal",
            "banding": "hidden",
        }
    return changed


def plugin_fingerprint(document: dict) -> str:
    plugins = [
        element for element in iter_elements(document)
        if element.get("kind") == "plugin"
    ]
    plugins.sort(key=lambda element: element.get("id", ""))
    return json.dumps(plugins, sort_keys=True)


def retheme_document(live: dict) -> tuple[dict, int, int]:
    document = copy.deepcopy(live)
    before = plugin_fingerprint(document)

    restyled = 0
    skipped = 0
    for element in iter_elements(document):
        if element.get("kind") == "plugin":
            skipped += 1
            continue
        if restyle_element(element):
            restyled += 1

    settings = document.setdefault("settings", {})
    settings.setdefault("theme", {})["overrides"] = THEME_OVERRIDES

    after = plugin_fingerprint(document)
    if before != after:
        raise RuntimeError("Refusing to publish: a plugin element was modified")
    return document, restyled, skipped


# ---------------------------------------------------------------- transport


def read_env(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if path.exists():
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    for key in ("SIGMA_BASE_URL", "SIGMA_API_BASE", "SIGMA_CLIENT_ID",
                "SIGMA_CLIENT_SECRET"):
        if key not in values and os.environ.get(key):
            values[key] = os.environ[key]
    return values


class SigmaApi:
    def __init__(self, env: dict[str, str], base: str | None = None):
        self.base = base or env.get("SIGMA_API_BASE") or env.get("SIGMA_BASE_URL")
        client_id = env.get("SIGMA_CLIENT_ID")
        client_secret = env.get("SIGMA_CLIENT_SECRET")
        if not self.base or not client_id or not client_secret:
            raise RuntimeError("Sigma base URL, client id and client secret are required")
        credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        request = urllib.request.Request(
            self.base + "/v2/auth/token",
            data=urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
            headers={
                "Authorization": "Basic " + credentials,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=40) as response:
            self.token = json.load(response)["access_token"]

    def call(self, method: str, path: str, body=None):
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Authorization": "Bearer " + self.token, "Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self.base + path, data=data, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=240) as response:
                raw = response.read().decode()
        except urllib.error.HTTPError as error:
            raise RuntimeError(
                f"Sigma {method} {path} failed ({error.code}): "
                + error.read().decode()[:2000]
            ) from None
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except ValueError:
            return {"raw": raw}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=pathlib.Path,
                        default=pathlib.Path("/workspace/.env"))
    parser.add_argument("--base", help="override the Sigma API host")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("verify")
    sub.add_parser("create")
    update = sub.add_parser("update")
    update.add_argument("workbook_id")
    update.add_argument("--expected-version", type=int, required=True)
    retheme = sub.add_parser("retheme")
    retheme.add_argument("workbook_id")
    retheme.add_argument("--publish", action="store_true")

    args = parser.parse_args()
    api = SigmaApi(read_env(args.env_file), args.base)

    if args.command == "retheme":
        live = api.call("GET", f"/v2/workbooks/{args.workbook_id}/spec")
        document = live.get("document", live)
        themed, restyled, skipped = retheme_document(document)
        print(f"restyled {restyled} elements, preserved {skipped} plugin elements")
        if not args.publish:
            print("dry run — pass --publish to write")
            return
        payload = {"name": live.get("name"), "document": themed}
        if live.get("folderId"):
            payload["folderId"] = live["folderId"]
        print(json.dumps(api.call(
            "PUT", f"/v2/workbooks/{args.workbook_id}/spec", payload), indent=2))
        return

    spec = build_spec()
    if args.command == "verify":
        print(json.dumps(api.call("POST", "/v2/workbooks/spec/verify", spec), indent=2))
        return
    if args.command == "create":
        result = api.call("POST", "/v2/workbooks/spec", spec)
        print(json.dumps(result, indent=2))
        if result.get("workbookId"):
            (HERE / "workbook_id.txt").write_text(result["workbookId"] + "\n")
        return

    meta = api.call("GET", f"/v2/workbooks/{args.workbook_id}")
    if meta.get("latestVersion") != args.expected_version:
        raise RuntimeError(
            f"Live version is {meta.get('latestVersion')}, "
            f"expected {args.expected_version}"
        )
    print(json.dumps(api.call(
        "PUT", f"/v2/workbooks/{args.workbook_id}/spec", spec), indent=2))


if __name__ == "__main__":
    main()
