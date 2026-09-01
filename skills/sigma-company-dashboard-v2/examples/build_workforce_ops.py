"""Build the "Hours & overtime" workforce-ops dashboard in papercranestaging.

A native-Sigma-styled single-page workbook (real Sigma logo/breadcrumb/colors,
light canvas) with REAL functioning filters: Site, Employment, Shift, and the
Current/Previous/Quarter period tabs all actually change the numbers shown --
they are not decorative. The underlying fact table is generated at
department x site x shift x employment x period grain (384 rows), built so
that the default filter state (Hourly, all sites, all shifts, Current period)
reproduces the original reference numbers exactly (largest-remainder integer
splits, not floating rescale, so sums are exact by construction).

"Hours by department" is a TABLE with a dataBars conditional format, not a
bar-chart -- a vertical grouped-category bar chart was structurally the wrong
shape for the reference's horizontal proportional-bar-per-row look.

All data is literal synthetic SQL (VALUES rows), executed through the
"Snowflake" connection (a9d45cfe-ff65-4515-8193-a7072602a1ee) on
papercranestaging -- confirmed live to resolve queries even though its
/connections/{id}/test health-check 500s (a flaky check, not a real outage).

Usage: python3 build_workforce_ops.py [create|verify|update <id>]
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import sigmaapi as S

PAPERCRANE_ORG_ID = "8c99818a-90b3-4cae-bdb7-cf69a741171a"
CONN = "a9d45cfe-ff65-4515-8193-a7072602a1ee"

# ---------------------------------------------------------------- palette
# Real Sigma brand tokens (sigma-brand-guidelines skill / colors_and_type.css).
CANVAS = "#F7F7F8"        # --sigma-surface
CARD = "#FFFFFF"          # --sigma-white
BORDER = "#E5E5E9"        # --sigma-line
INK = "#111114"           # --sigma-ink / --fg-1
MUTED = "#5F5F66"         # --sigma-slate / --fg-3
BLUE = "#1A70F1"          # --sigma-blue
BLUE_TINT = "#EEF3FF"     # --sigma-blue-tint
ORANGE = "#C77A0A"        # --sigma-warning
GOOD = "#1F9D55"          # --sigma-success
BAD = "#D14343"           # --sigma-danger
STATUS_COLOR = {"Watch": ORANGE, "Over plan": BAD, "On plan": MUTED}

NUM0 = {"kind": "number", "formatString": ",.0f"}
NUM1 = {"kind": "number", "formatString": ",.1f"}
MONEYK = {"kind": "number", "formatString": "$,.3s", "currencySymbol": "$"}
PCT1 = {"kind": "number", "formatString": ".1%"}

elements, overlays, agents = [], [], []


def add(el):
    elements.append(el)
    return el["id"]


def panel(pad=None):
    s = {"backgroundColor": CARD, "borderColor": BORDER, "borderWidth": 1, "borderRadius": "round"}
    if pad:
        s["padding"] = pad
    return s


def title(text, size=13):
    return {"text": text, "color": INK, "fontSize": size}


def disp(c):
    return " ".join(w.capitalize() for w in c.split("_"))


# ============================================================== fact table
# department, headcount(Hourly), regular_hrs, overtime_hrs, ot_cost, status, sort_order
DEPTS = [
    ("Fulfillment",       88, 3344, 412, 19000, "Watch",     1),
    ("Assembly",          64, 2432, 318, 18000, "Watch",     2),
    ("Customer support",  57, 2166,  88,  4000, "On plan",   3),
    ("Logistics",         45, 1710, 243, 12000, "Watch",     4),
    ("Quality",           31, 1178,  74,  4000, "On plan",   5),
    ("Engineering",       26, 1014,  39,  3000, "On plan",   6),
    ("Maintenance",       22,  836, 196, 13000, "Over plan", 7),
    ("Facilities",        18,  684, 121,  7000, "Over plan", 8),
]

SITES = ["Denver", "Dallas", "Atlanta", "Phoenix"]
SITE_SHARE = [0.30, 0.27, 0.24, 0.19]
SHIFTS = ["Day", "Evening", "Night"]
SHIFT_SHARE = [0.46, 0.34, 0.20]
PERIODS = ["Current", "Previous", "Quarter"]
PERIOD_SCALE = {"Current": 1.0, "Previous": 0.982, "Quarter": 6.5}


def split_exact(total, weights):
    """Largest-remainder integer split -- sums to `total` exactly, unlike a
    naive proportional round which can drift by 1-2 units per row."""
    total = int(round(total))
    s = sum(weights) or 1
    raw = [total * w / s for w in weights]
    floors = [int(x) for x in raw]
    remainder = total - sum(floors)
    order = sorted(range(len(weights)), key=lambda i: -(raw[i] - floors[i]))
    for i in range(max(remainder, 0)):
        floors[order[i % len(order)]] += 1
    return floors


FACT_COLS = ["department", "site", "shift", "employment", "pay_period",
             "headcount", "regular_hrs", "overtime_hrs", "total_hrs", "ot_cost",
             "baseline_regular_hrs", "baseline_overtime_hrs", "baseline_total_hrs", "baseline_ot_cost",
             "status", "sort_order"]

FACT = []  # list of dicts, keyed by FACT_COLS

for name, hc, reg, ot, cost, status, order in DEPTS:
    site_shift_w = [s * sh for s in SITE_SHARE for sh in SHIFT_SHARE]
    hc_split = split_exact(hc, site_shift_w)
    # Compute all three periods' splits up front so every row (regardless of
    # its OWN period) can carry the "Previous" split as a constant baseline --
    # this lets a KPI show "vs Previous" without needing to reference the
    # Period control's live value inside a formula (that reference silently
    # fails: "[Period]" resolves as an unknown column, not the control).
    splits = {}
    for period in PERIODS:
        scale = PERIOD_SCALE[period]
        reg_split = split_exact(reg * scale, site_shift_w)
        ot_split = split_exact(ot * scale, site_shift_w)
        cost_split = split_exact(cost * scale, [max(v, 0.0001) for v in ot_split])
        splits[period] = (reg_split, ot_split, cost_split)
    base_reg, base_ot, base_cost = splits["Previous"]
    for period in PERIODS:
        reg_split, ot_split, cost_split = splits[period]
        idx = 0
        for site in SITES:
            for shift in SHIFTS:
                r, o = reg_split[idx], ot_split[idx]
                br, bo = base_reg[idx], base_ot[idx]
                FACT.append(dict(zip(FACT_COLS, [
                    name, site, shift, "Hourly", period,
                    hc_split[idx], r, o, r + o, cost_split[idx],
                    br, bo, br + bo, base_cost[idx], status, order])))
                idx += 1
    # Salaried: same 4 sites, single (Day) shift, ~15% of hourly headcount/hours, exempt (no OT cost)
    s_hc_split = split_exact(hc * 0.15, SITE_SHARE)
    s_splits = {}
    for period in PERIODS:
        scale = PERIOD_SCALE[period]
        s_splits[period] = (split_exact(reg * 0.15 * scale, SITE_SHARE),
                             split_exact(ot * 0.03 * scale, SITE_SHARE))
    s_base_reg, s_base_ot = s_splits["Previous"]
    for period in PERIODS:
        s_reg_split, s_ot_split = s_splits[period]
        for i, site in enumerate(SITES):
            r, o = s_reg_split[i], s_ot_split[i]
            br, bo = s_base_reg[i], s_base_ot[i]
            FACT.append(dict(zip(FACT_COLS, [
                name, site, "Day", "Salaried", period,
                s_hc_split[i], r, o, r + o, 0,
                br, bo, br + bo, 0, status, order])))


def sql_values(rows):
    return ",\n    ".join(
        "(" + ", ".join("'%s'" % v.replace("'", "''") if isinstance(v, str) else str(v) for v in row) + ")"
        for row in rows)


fact_sql = ("SELECT * FROM VALUES\n    %s\n  AS f(%s)"
            % (sql_values([tuple(r[c] for c in FACT_COLS) for r in FACT]), ", ".join(FACT_COLS)))

# Sanity check at build time: default filter state (Hourly/Current/all sites/shifts)
# must reproduce the exact reference totals.
_chk = [r for r in FACT if r["employment"] == "Hourly" and r["pay_period"] == "Current"]
assert sum(r["headcount"] for r in _chk) == sum(d[1] for d in DEPTS), "headcount mismatch"
assert sum(r["regular_hrs"] for r in _chk) == sum(d[2] for d in DEPTS), "regular_hrs mismatch"
assert sum(r["overtime_hrs"] for r in _chk) == sum(d[3] for d in DEPTS), "overtime_hrs mismatch"
assert sum(r["ot_cost"] for r in _chk) == sum(d[4] for d in DEPTS), "ot_cost mismatch"

TREND = [
    ("Jun 15", 1, 700), ("Jun 22", 2, 735), ("Jun 29", 3, 690),
    ("Jul 6", 4, 745), ("Jul 13", 5, 705), ("Jul 20", 6, 780),
    ("Jul 27", 7, 654), ("Aug 3", 8, 887),
]
trend_sql = "SELECT * FROM VALUES\n    %s\n  AS t(week_label, week_order, ot_hours)" % sql_values(TREND)

FLAGGED = [
    ("Marisol Vega",  "Maintenance", 6, 58.5, 18.5, 1),
    ("Dee Okonkwo",   "Fulfillment", 6, 56.0, 16.0, 2),
    ("Tomas Beck",    "Assembly",    5, 54.5, 14.5, 3),
    ("Priya Raman",   "Maintenance", 5, 52.0, 12.0, 4),
    ("Owen Hartley",  "Logistics",   6, 51.5, 11.5, 5),
    ("Nina Castellan", "Fulfillment", 5, 49.0,  9.0, 6),
]
flagged_sql = ("SELECT * FROM VALUES\n    %s\n  AS f(employee_name, department, shifts, total_hrs, ot_hrs, sort_order)"
               % sql_values(FLAGGED))

kpi_meta_sql = "SELECT 34 AS flagged_count, 5 AS flagged_delta"


def sql_table(eid, name, statement, colnames):
    add({"id": eid, "kind": "table", "name": name,
         "source": {"connectionId": CONN, "kind": "sql", "statement": statement},
         "columns": [{"id": "%s-%d" % (eid, i), "formula": "[Custom SQL/%s]" % c, "name": disp(c)}
                     for i, c in enumerate(colnames)]})


sql_table("tbl-fact", "Fact", fact_sql, FACT_COLS)
sql_table("tbl-trend", "OT Trend", trend_sql, ["week_label", "week_order", "ot_hours"])
sql_table("tbl-flagged", "Flagged", flagged_sql, ["employee_name", "department", "shifts", "total_hrs", "ot_hrs", "sort_order"])
sql_table("tbl-kpi-meta", "KPI Meta", kpi_meta_sql, ["flagged_count", "flagged_delta"])


def fact_view(eid, name):
    """A pass-through child of tbl-fact so different consumer groups can carry
    independent control filters (kc-total/kc-ot/kc-cost need Site/Shift/
    Employment filtered but NOT Period, since Period is handled in-formula so
    the comparison column can still reach the 'Previous' rows)."""
    add({"id": eid, "kind": "table", "name": name,
         "source": {"elementId": "tbl-fact", "kind": "table"},
         "columns": [{"id": "%s-%s" % (eid, c), "formula": "[Fact/%s]" % disp(c), "name": disp(c)}
                     for c in FACT_COLS]})


fact_view("vf", "Fact (filtered view)")   # site+shift+employment+period all native-filtered
fact_view("vc", "Fact (compare view)")    # site+shift+employment native-filtered; period via formula

# ---------------------------------------------------------------- header
LOGO_URI = (pathlib.Path(__file__).with_name("assets") / "sigma_logo_shadowblack.datauri.txt").read_text().strip()
add({"id": "hdr-logo", "kind": "image", "source": {"kind": "url", "url": LOGO_URI},
     "style": {"fit": "contain", "align": "start", "padding": "none"}})
add({"id": "hdr-crumb", "kind": "text",
     "body": ('<span style="color:%s">Workforce ops</span>  <span style="color:%s">&#8250;</span>  '
              '**Hours & overtime**' % (MUTED, MUTED)),
     "style": {"color": INK, "backgroundColor": CANVAS, "padding": "none"}, "verticalAlign": "middle"})
add({"id": "hdr-live", "kind": "text", "body": '<span style="color:%s">&#8635; **Live**</span>' % BLUE,
     "style": {"color": BLUE, "backgroundColor": BLUE_TINT}, "verticalAlign": "middle"})

# ---------------------------------------------------------------- controls
# Period: NOT bound as a native row-filter on vc (kc-total/kc-ot/kc-cost read
# from vc and reference {{Period}}'s value inside SumIf so the comparison
# column can still see "Previous" rows). It IS a native filter on vf (bar
# table, department detail, OT-share KPI), where no comparison is needed.
FACT_TARGETS = ["vf", "vc"]


VIEW_NAME = {"vf": "Fact (filtered view)", "vc": "Fact (compare view)"}


def col_of(view, name):
    """Internal column id -- valid for filters' columnId, NOT for formulas."""
    return "%s-%s" % (view, name)


def vcol(view, name):
    """Cross-element formula reference: [Element Name/Column Display Name]."""
    return "[%s/%s]" % (VIEW_NAME[view], disp(name))


def filters_for(col_name, views=FACT_TARGETS):
    return [{"source": {"kind": "table", "elementId": v}, "columnId": col_of(v, col_name)} for v in views]


add({"id": "ctrl-period", "kind": "control", "controlId": "cid-period", "name": "Period",
     "controlType": "segmented", "source": {"kind": "manual", "valueType": "text",
                                             "values": PERIODS},
     "value": "Current", "filters": filters_for("pay_period")})
add({"id": "txt-payperiod", "kind": "text", "body": "**Pay period** Jul 27 – Aug 9",
     "style": {"backgroundColor": CANVAS, "padding": "none"}, "verticalAlign": "middle"})


def multi_filter(eid, cid, name, values):
    return add({"id": eid, "kind": "control", "controlId": cid, "name": name,
                "controlType": "list", "mode": "include", "selectionMode": "multiple",
                "values": [], "source": {"kind": "manual", "valueType": "text", "values": values},
                "filters": filters_for(cid.replace("cid-", ""))})


def single_filter(eid, cid, name, values, default, col_name):
    return add({"id": eid, "kind": "control", "controlId": cid, "name": name,
                "controlType": "list", "mode": "include", "selectionMode": "single",
                "value": default, "source": {"kind": "manual", "valueType": "text", "values": values},
                "filters": filters_for(col_name)})


multi_filter("ctrl-site", "cid-site", "Site", SITES)
single_filter("ctrl-emp", "cid-emp", "Employment", ["Hourly", "Salaried"], "Hourly", "employment")
multi_filter("ctrl-shift", "cid-shift", "Shift", SHIFTS)

# ---------------------------------------------------------------- KPI cards
def kpi_dynamic(eid, label, col, fmt, sub, invert=False):
    """Value = Sum over whatever Site/Shift/Employment/Period the controls
    currently select (native row filters on vc). Comparison reads the
    embedded "baseline_<col>" (the Previous period's number for that same
    slice, carried on every row) -- this avoids referencing the Period
    control's live value inside a formula, which does not resolve (a
    control's value is only usable where it is already bound as a filter)."""
    value_ref = vcol("vc", col)
    baseline_ref = vcol("vc", "baseline_" + col)
    cols = [{"id": eid + "-v", "formula": "Sum(%s)" % value_ref, "name": label, "format": fmt},
            {"id": eid + "-c", "formula": "Sum(%s)" % baseline_ref, "name": "Prior", "format": fmt}]
    add({"id": eid, "kind": "kpi-chart", "source": {"elementId": "vc", "kind": "table"},
         "columns": cols, "value": {"columnId": eid + "-v", "color": INK, "fontSize": 30},
         "comparisonColumn": {"columnId": eid + "-c"},
         "comparison": {"display": "delta", "colorGood": BAD if invert else GOOD,
                        "colorBad": GOOD if invert else BAD},
         "name": title(label.upper(), 11), "style": panel(), "layout": {"anchor": "middle"}})
    add({"id": eid + "-sub", "kind": "text", "body": sub,
         "style": {"color": MUTED, "backgroundColor": CANVAS, "padding": "none"}})


def kpi_static_ratio(eid, label, num_col, den_col, fmt, sub):
    """No comparison -- just the live Sum ratio over whatever vf's native
    filters (site/shift/employment/period) currently select."""
    cols = [{"id": eid + "-n", "formula": "Sum(%s)" % vcol("vf", num_col), "name": "n"},
            {"id": eid + "-d", "formula": "Sum(%s)" % vcol("vf", den_col), "name": "d"},
            {"id": eid + "-v", "formula": "[n] / NullIf([d], 0)", "name": label, "format": fmt}]
    add({"id": eid, "kind": "kpi-chart", "source": {"elementId": "vf", "kind": "table"},
         "columns": cols, "value": {"columnId": eid + "-v", "color": INK, "fontSize": 30},
         "name": title(label.upper(), 11), "style": panel(), "layout": {"anchor": "middle"}})
    add({"id": eid + "-sub", "kind": "text", "body": sub,
         "style": {"color": MUTED, "backgroundColor": CANVAS, "padding": "none"}})


def kpi_meta(eid, label, col, fmt, sub):
    add({"id": eid, "kind": "kpi-chart", "source": {"elementId": "tbl-kpi-meta", "kind": "table"},
         "columns": [{"id": eid + "-v", "formula": "[KPI Meta/%s]" % disp(col), "name": label, "format": fmt}],
         "value": {"columnId": eid + "-v", "color": INK, "fontSize": 30},
         "name": title(label.upper(), 11), "style": panel(), "layout": {"anchor": "middle"}})
    add({"id": eid + "-sub", "kind": "text", "body": sub,
         "style": {"color": MUTED, "backgroundColor": CANVAS, "padding": "none"}})


kpi_dynamic("kc-total", "Total Hours", "total_hrs", NUM0, "vs Previous period")
kpi_dynamic("kc-ot", "Overtime Hours", "overtime_hrs", NUM0, "vs Previous period", invert=True)
kpi_static_ratio("kc-share", "OT Share of Hours", "overtime_hrs", "total_hrs", PCT1, "target 10%")
kpi_dynamic("kc-cost", "Overtime Cost", "ot_cost", MONEYK, "vs Previous period", invert=True)
kpi_meta("kc-flag", "Timesheets Flagged", "flagged_count", NUM0, "over 45 hours in a week (org-wide, unfiltered)")

# ---------------------------------------------------------------- hours by department
# A TABLE with a dataBars conditional format -- horizontal proportional bars
# per row, matching the reference. (A vertical grouped-category bar chart, my
# first pass, was structurally the wrong chart type for this.)
add({"id": "bar-dept", "kind": "table", "name": "Hours by department",
     "description": {"visibility": "shown", "text": "Regular and overtime hours for the selected period"},
     "source": {"elementId": "vf", "kind": "table"},
     "columns": [
         {"id": "bd-name", "formula": vcol("vf", "department"), "name": "Department"},
         {"id": "bd-sort", "formula": "Min(%s)" % vcol("vf", "sort_order"), "name": "Sort"},
         {"id": "bd-total", "formula": "Sum(%s)" % vcol("vf", "total_hrs"), "name": "Total hrs", "format": NUM0},
         {"id": "bd-ot", "formula": "Sum(%s)" % vcol("vf", "overtime_hrs"), "name": "Overtime hrs", "format": NUM0},
         {"id": "bd-pct", "formula": "[Overtime hrs] / NullIf([Total hrs], 0)", "name": "OT %", "format": PCT1}],
     "groupings": [{"id": "bdg", "groupBy": ["bd-name"],
                    "calculations": ["bd-sort", "bd-total", "bd-ot", "bd-pct"],
                    "sort": [{"columnId": "bd-sort", "direction": "ascending"}]}],
     "conditionalFormats": [
         {"type": "dataBars", "columnIds": ["bd-total"], "scheme": [BLUE_TINT, BLUE]},
         {"type": "single", "columnIds": ["bd-pct"], "condition": ">=", "value": 0.1,
          "style": {"backgroundColor": BLUE_TINT, "color": ORANGE, "bold": True}}],
     "tableComponents": {"summaryBar": "hidden"},
     "style": panel()})

# ---------------------------------------------------------------- overtime trend panel
add({"id": "c-trend", "kind": "container", "style": panel(), "layout": {"gridTemplateRows": "auto"}})
add({"id": "trend-title", "kind": "text",
     "body": "**Overtime trend**\n<span style=\"color:%s\">All departments · last 8 weeks</span>" % MUTED,
     "style": {"backgroundColor": CARD, "padding": "none"}})
add({"id": "kc-peak", "kind": "kpi-chart", "source": {"elementId": "tbl-trend", "kind": "table"},
     "columns": [{"id": "kcp-v", "formula": "SumIf([OT Trend/Ot Hours], [OT Trend/Week Order] = 8)",
                  "name": "OT hours last week", "format": NUM0}],
     "value": {"columnId": "kcp-v", "color": INK, "fontSize": 30},
     "name": title("OT HOURS LAST WEEK", 11),
     "style": {"backgroundColor": CARD, "padding": "none"}, "layout": {"anchor": "middle"}})
add({"id": "line-trend", "kind": "line-chart", "source": {"elementId": "tbl-trend", "kind": "table"},
     "columns": [{"id": "lt-x", "formula": "[OT Trend/Week Label]", "name": "Week"},
                 {"id": "lt-y", "formula": "[OT Trend/Ot Hours]", "name": "OT Hours", "format": NUM0}],
     "xAxis": {"columnId": "lt-x"}, "yAxis": {"columnIds": ["lt-y"]},
     "colorAssignment": {"palette": {"scheme": [BLUE], "type": "categorical"}},
     "lineAreaStyle": {"interpolation": "linear", "area": "shown"},
     "legend": {"visibility": "hidden"}, "style": {"backgroundColor": CARD, "padding": "none"}})
add({"id": "trend-stats", "kind": "text",
     "body": "Weekly average **737 hrs**  \nPeak week **887 hrs**  \nShare of hours **10.0%**",
     "style": {"color": INK, "backgroundColor": CARD, "padding": "none"}})

# ---------------------------------------------------------------- department detail
add({"id": "tbl-detail", "kind": "table", "name": "Department detail",
     "source": {"elementId": "vf", "kind": "table"},
     "columns": [
         {"id": "td-name", "formula": vcol("vf", "department"), "name": "Department"},
         {"id": "td-hc", "formula": "Sum(%s)" % vcol("vf", "headcount"), "name": "Headcount", "format": NUM0},
         {"id": "td-reg", "formula": "Sum(%s)" % vcol("vf", "regular_hrs"), "name": "Regular hrs", "format": NUM0},
         {"id": "td-ot", "formula": "Sum(%s)" % vcol("vf", "overtime_hrs"), "name": "Overtime hrs", "format": NUM0},
         {"id": "td-pct", "formula": "[Overtime hrs] / NullIf([Regular hrs] + [Overtime hrs], 0)", "name": "OT %", "format": PCT1},
         {"id": "td-cost", "formula": "Sum(%s)" % vcol("vf", "ot_cost"), "name": "OT cost", "format": MONEYK},
         {"id": "td-badge", "formula": 'Concat("● ", Min(%s))' % vcol("vf", "status"), "name": "Status"}],
     "groupings": [{"id": "tdg", "groupBy": ["td-name"],
                    "calculations": ["td-hc", "td-reg", "td-ot", "td-pct", "td-cost", "td-badge"],
                    "sort": [{"columnId": "td-ot", "direction": "descending"}]}],
     "conditionalFormats": [
         {"type": "single", "columnIds": ["td-badge"], "condition": "=", "value": "● " + status,
          "style": {"backgroundColor": CARD, "color": color, "bold": status != "On plan"}}
         for status, color in STATUS_COLOR.items()],
     "tableComponents": {"summaryBar": "hidden"},
     "style": panel()})

# ---------------------------------------------------------------- flagged timesheets
add({"id": "tbl-flag-list", "kind": "table", "name": "Over 45 hours this period",
     "source": {"elementId": "tbl-flagged", "kind": "table"},
     "columns": [
         {"id": "fl-name", "formula": "[Flagged/Employee Name]", "name": "Employee"},
         {"id": "fl-dept", "formula": "[Flagged/Department]", "name": "Department"},
         {"id": "fl-shifts", "formula": "[Flagged/Shifts]", "name": "Shifts", "format": NUM0},
         {"id": "fl-hrs", "formula": "[Flagged/Total Hrs]", "name": "Hours", "format": NUM1},
         {"id": "fl-ot", "formula": "[Flagged/Ot Hrs]", "name": "OT", "format": NUM1}],
     "sort": [{"columnId": "fl-ot", "direction": "descending"}],
     "description": {"visibility": "shown", "text": "Across all departments (unfiltered)"},
     "tableComponents": {"summaryBar": "hidden"},
     "style": panel()})
add({"id": "txt-seeall", "kind": "text", "body": "[See all flagged timesheets →](#)",
     "style": {"color": BLUE, "backgroundColor": CANVAS, "padding": "none"}})

# ---------------------------------------------------------------- Sigma Assistant
agents.append({"id": "ag-wf", "name": "Workforce Ops Assistant",
               "instructions": ("Answer questions about hours, overtime, and departments using the "
                                 "Fact, OT Trend, and Flagged data sources. Be concise."),
               "dataSources": [{"elementId": "tbl-fact", "kind": "table"},
                                {"elementId": "tbl-trend", "kind": "table"},
                                {"elementId": "tbl-flagged", "kind": "table"}]})
add({"id": "c-assistant", "kind": "container", "style": panel(), "layout": {"gridTemplateRows": "auto"}})
add({"id": "assist-title", "kind": "text", "body": "**⚙ SIGMA ASSISTANT**",
     "style": {"color": BLUE, "backgroundColor": CARD, "padding": "none"}})
add({"id": "assist-insight", "kind": "text",
     "body": ("Maintenance and Fulfillment account for 41% of overtime hours while holding "
              "31% of headcount. Both trend up 3 weeks running."),
     "style": {"color": INK, "backgroundColor": CARD, "padding": "none"}})
add({"id": "chat-wf", "kind": "chat", "agentId": "ag-wf"})

# ---------------------------------------------------------------- footer
add({"id": "txt-source", "kind": "text",
     "body": ("Source: timekeeping.shifts joined to hr.employees, refreshed hourly. "
              "Overtime is any hour logged past 40 in a week."),
     "style": {"color": MUTED, "backgroundColor": CANVAS, "padding": "none"}})

# ==================================================================== layout
LAYOUT = """<?xml version="1.0" encoding="utf-8"?>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg1">
  <Element elementId="hdr-logo" gridColumn="1 / 3" gridRow="1 / 4"/>
  <Element elementId="hdr-crumb" gridColumn="3 / 10" gridRow="1 / 4"/>
  <Element elementId="hdr-live" gridColumn="10 / 12" gridRow="1 / 4"/>

  <Element elementId="ctrl-period" gridColumn="1 / 6" gridRow="5 / 7"/>
  <Element elementId="txt-payperiod" gridColumn="6 / 11" gridRow="5 / 7"/>
  <Element elementId="ctrl-site" gridColumn="14 / 18" gridRow="5 / 7"/>
  <Element elementId="ctrl-emp" gridColumn="18 / 21" gridRow="5 / 7"/>
  <Element elementId="ctrl-shift" gridColumn="21 / 25" gridRow="5 / 7"/>

  <Element elementId="kc-total" gridColumn="1 / 6" gridRow="7 / 12"/>
  <Element elementId="kc-total-sub" gridColumn="1 / 6" gridRow="12 / 13"/>
  <Element elementId="kc-ot" gridColumn="6 / 11" gridRow="7 / 12"/>
  <Element elementId="kc-ot-sub" gridColumn="6 / 11" gridRow="12 / 13"/>
  <Element elementId="kc-share" gridColumn="11 / 15" gridRow="7 / 12"/>
  <Element elementId="kc-share-sub" gridColumn="11 / 15" gridRow="12 / 13"/>
  <Element elementId="kc-cost" gridColumn="15 / 20" gridRow="7 / 12"/>
  <Element elementId="kc-cost-sub" gridColumn="15 / 20" gridRow="12 / 13"/>
  <Element elementId="kc-flag" gridColumn="20 / 25" gridRow="7 / 12"/>
  <Element elementId="kc-flag-sub" gridColumn="20 / 25" gridRow="12 / 13"/>

  <Element elementId="bar-dept" gridColumn="1 / 15" gridRow="13 / 29"/>
  <Container elementId="c-trend" type="grid" gridColumn="15 / 25" gridRow="13 / 29" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="trend-title" gridColumn="1 / 13" gridRow="1 / 2"/>
    <Element elementId="kc-peak" gridColumn="1 / 13" gridRow="2 / 6"/>
    <Element elementId="line-trend" gridColumn="1 / 13" gridRow="6 / 13"/>
    <Element elementId="trend-stats" gridColumn="1 / 13" gridRow="13 / 15"/>
  </Container>

  <Element elementId="tbl-detail" gridColumn="1 / 15" gridRow="29 / 46"/>
  <Element elementId="tbl-flag-list" gridColumn="15 / 25" gridRow="29 / 38"/>
  <Element elementId="txt-seeall" gridColumn="15 / 25" gridRow="38 / 39"/>
  <Container elementId="c-assistant" type="grid" gridColumn="15 / 25" gridRow="39 / 46" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="assist-title" gridColumn="1 / 13" gridRow="1 / 2"/>
    <Element elementId="assist-insight" gridColumn="1 / 13" gridRow="2 / 4"/>
    <Element elementId="chat-wf" gridColumn="1 / 13" gridRow="4 / 7"/>
  </Container>

  <Element elementId="txt-source" gridColumn="1 / 25" gridRow="46 / 47"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pgData">
  <Element elementId="tbl-fact" gridColumn="1 / 9" gridRow="1 / 13"/>
  <Element elementId="vf" gridColumn="9 / 17" gridRow="1 / 13"/>
  <Element elementId="vc" gridColumn="17 / 25" gridRow="1 / 13"/>
  <Element elementId="tbl-trend" gridColumn="1 / 9" gridRow="13 / 25"/>
  <Element elementId="tbl-flagged" gridColumn="9 / 17" gridRow="13 / 25"/>
  <Element elementId="tbl-kpi-meta" gridColumn="17 / 25" gridRow="13 / 25"/>
</Page>"""

SPEC = {
    "name": "Hours & overtime",
    "folderId": "00000000-0000-0000-0000-000000000000",
    "document": {
        "schemaVersion": 1,
        "kind": "workbook",
        "elements": elements,
        "pages": [{"id": "pg1", "name": "Hours & overtime"},
                  {"id": "pgData", "name": "Data", "visibility": "hidden"}],
        "layout": LAYOUT,
        "overlays": overlays,
        "agents": agents,
        "settings": {"theme": {"overrides": {"colors": {
            "surface": CANVAS, "text": INK, "highlight": BLUE,
            "success": GOOD, "warning": ORANGE, "danger": BAD}}}},
    },
}


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "verify"
    who = S.call("GET", "/v2/whoami")
    if who.get("organizationId") != PAPERCRANE_ORG_ID:
        print("Refusing to write: not papercranestaging (org=%s)" % who.get("organizationId"))
        sys.exit(1)
    if action == "verify":
        try:
            S.verify_workbook(SPEC)
            print("verify passed —", len(elements), "elements,", len(FACT), "fact rows")
        except S.SigmaError as exc:
            print("verify failed:", str(exc.body)[:2500])
    elif action == "create":
        r = S.create_workbook(SPEC)
        print("created", r["workbookId"])
        meta = S.get_workbook_meta(r["workbookId"])
        print("urlId:", meta.get("workbookUrlId") or meta.get("url"))
        pathlib.Path(__file__).with_name("workforce_ops_id.txt").write_text(r["workbookId"])
    elif action == "update":
        workbook_id = sys.argv[2]
        S.update_workbook(workbook_id, SPEC)
        print("updated", workbook_id)


if __name__ == "__main__":
    main()
