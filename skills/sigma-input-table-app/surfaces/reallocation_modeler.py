"""Pluggable reallocation / scenario modeler surface — control-driven bulk
shift over a baseline, with a capacity constraint check.

Generalized from build_scenario_approval_workbench.py (itself debugged live
2026-08-13) and the Honda EV allocation example's constraint-check idiom.
Bakes in two hard-won, previously undocumented findings:

  * A bulk "what-if" lever MUST be a computed column reading a control, never
    an update-rows action with a per-row formula value fired from a button --
    that has no row context and fails only on a real click (passes verify/
    create either way). See sigma-input-table-app/reference/
    approval-workflow-pattern.md.
  * Any `control` element referenced by a formula column must be declared
    EARLIER in `document.elements` than the column referencing it, or the
    column fails at render time with a misleading "Reference to errored
    column" error that doesn't mention ordering at all. See
    scenario-modeler-pattern.md. This module's `elements` list is already
    ordered correctly -- keep the control block first if you reorder anything.

The compelling "Honda" narrative move -- naming the actual binding constraint,
not just showing a chart -- is generalized as the capacity-constraint grouped
table: which dimension value(s) breach capacity, with status pills.

Usage:

    import surfaces_reallocation_modeler as reallocation
    r = reallocation.build(
        prefix="rl", connection_id=CONN,
        dimension_columns=[{"id": "category", "name": "Category"},
                            {"id": "region", "name": "Region"}],
        baseline_sql='''SELECT * FROM VALUES (...) AS t(category, region, baseline_units, capacity_units)''',
        capacity_dimension_id="region",  # which dimension the constraint is grouped/checked by
    )
    elements += r["elements"]; pages += r["pages"]; layout += r["layout_xml"]
    # r["unplaced"] has nothing to place elsewhere by default -- this module
    # owns a single self-contained page. Merge its `page_id` into your
    # navigation if you want it alongside other surfaces/pages.
"""


def build(
    prefix,
    connection_id,
    dimension_columns,
    baseline_sql,
    capacity_dimension_id,
    measure_label="Units",
    page_name="Reallocation Planner",
    embed=False,
):
    """`dimension_columns`: list of {"id","name"} -- SQL column names (id) and
    display names for each grouping dimension, e.g.
    [{"id": "category", "name": "Category"}, {"id": "region", "name": "Region"}].
    `baseline_sql` must produce one row per full dimension combination plus
    two measure columns named BASELINE_UNITS and CAPACITY_UNITS (uppercase,
    matching Snowflake's default unquoted-identifier casing).
    `capacity_dimension_id` must be one of the dimension_columns ids -- the
    constraint check groups by this dimension (e.g. checking region-level
    capacity even though the grid models category x region).
    """
    p = prefix
    dim_ids = [d["id"] for d in dimension_columns]
    if capacity_dimension_id not in dim_ids:
        raise ValueError("capacity_dimension_id must be one of dimension_columns' ids")

    base_id = f"{p}-base"
    assum_id = f"{p}-assum"
    book_id = f"{p}-book"
    load_id = f"{p}-load"

    base_columns = [
        {"id": f"{p}-sb-{d['id']}", "formula": f"[Custom SQL/{d['id'].upper()}]", "name": d["name"]}
        for d in dimension_columns
    ] + [
        {"id": f"{p}-sb-units", "formula": "[Custom SQL/BASELINE_UNITS]", "name": f"Baseline {measure_label}"},
        {"id": f"{p}-sb-cap", "formula": "[Custom SQL/CAPACITY_UNITS]", "name": "Capacity"},
    ]
    base = {
        "id": base_id, "kind": "table", "name": "Reallocation Base", "visibleAsSource": True,
        "source": {"connectionId": connection_id, "kind": "sql", "statement": baseline_sql},
        "columns": base_columns,
    }

    # Bulk shift control -- MUST be declared before `assum` in the elements
    # list (see module docstring / scenario-modeler-pattern.md).
    ctrl_shift = {
        "id": f"ctrl-{p}-shift", "kind": "control", "controlId": f"{p}_shift_pct",
        "name": "Bulk shift %", "controlType": "number", "mode": "=", "value": 0,
        "includeNulls": "when-no-value-is-selected",
    }

    assum_dim_cols = [{"id": f"{p}-ia-{d['id']}", "key": f"{p}-sb-{d['id']}"} for d in dimension_columns]
    assum = {
        "id": assum_id, "kind": "input-table", "name": "Assumptions",
        "inputMode": "view", "source": {"kind": "linked", "from": base_id},
        "columns": [
            *assum_dim_cols,
            {"id": f"{p}-ia-units", "key": f"{p}-sb-units"},
            {"id": f"{p}-ia-cap", "key": f"{p}-sb-cap"},
            {"id": f"{p}-ia-proposed", "type": "number", "name": "Proposed"},
            {"id": f"{p}-ia-shiftfactor", "hidden": True, "name": "Shift Factor",
             "formula": f"1 + Coalesce([{p}_shift_pct], 0) / 100.0"},
            {"id": f"{p}-ia-scenario", "hidden": True, "name": "Scenario Units",
             "formula": f"Round([Baseline {measure_label}] * [Shift Factor])"},
            {"id": f"{p}-ia-eff", "name": f"Effective {measure_label}",
             "formula": "Coalesce([Proposed], [Scenario Units])",
             "format": {"kind": "number", "formatString": ",d"}},
            {"id": f"{p}-ia-var", "name": "Variance",
             "formula": f"[Effective {measure_label}] - [Baseline {measure_label}]",
             "format": {"kind": "number", "formatString": "+,d"}},
        ],
        "order": [c["id"] for c in assum_dim_cols] + [
            f"{p}-ia-units", f"{p}-ia-cap", f"{p}-ia-proposed", f"{p}-ia-eff", f"{p}-ia-var",
        ],
        "tableComponents": {"summaryBar": "hidden"},
    }

    book_cols = [
        {"id": f"{p}-bk-{d['id']}", "formula": f"[Assumptions/{d['name']}]", "name": d["name"]}
        for d in dimension_columns
    ] + [
        {"id": f"{p}-bk-units", "formula": f"[Assumptions/Baseline {measure_label}]",
         "name": f"Baseline {measure_label}"},
        {"id": f"{p}-bk-cap", "formula": "[Assumptions/Capacity]", "name": "Capacity"},
        {"id": f"{p}-bk-eff", "formula": f"[Assumptions/Effective {measure_label}]",
         "name": f"Effective {measure_label}"},
    ]
    book = {
        "id": book_id, "kind": "table", "name": "Book", "visibleAsSource": True,
        "source": {"elementId": assum_id, "kind": "table"},
        "columns": book_cols,
    }

    cap_dim = next(d for d in dimension_columns if d["id"] == capacity_dimension_id)
    load_columns = [
        {"id": f"{p}-ld-dim", "name": cap_dim["name"], "formula": f"[Book/{cap_dim['name']}]"},
        {"id": f"{p}-ld-eff", "name": "Allocated", "formula": f"Sum([Book/Effective {measure_label}])",
         "format": {"kind": "number", "formatString": ",d"}},
        {"id": f"{p}-ld-cap", "name": "Capacity", "formula": "Sum([Book/Capacity])",
         "format": {"kind": "number", "formatString": ",d"}},
        {"id": f"{p}-ld-util", "name": "Utilization",
         "formula": f"Sum([Book/Effective {measure_label}]) / Sum([Book/Capacity])",
         "format": {"kind": "number", "formatString": ".1%"}},
        {"id": f"{p}-ld-status", "name": "Capacity Status",
         "formula": (f'If(Sum([Book/Effective {measure_label}]) > Sum([Book/Capacity]), '
                     '"Over capacity", "Within capacity")')},
    ]
    load = {
        "id": load_id, "kind": "table", "name": "Capacity Load",
        "source": {"kind": "table", "elementId": book_id},
        "columns": load_columns,
        "groupings": [{"id": f"{p}-g-load", "groupBy": [f"{p}-ld-dim"],
                       "calculations": [f"{p}-ld-eff", f"{p}-ld-cap", f"{p}-ld-util", f"{p}-ld-status"]}],
        "conditionalFormats": [
            {"type": "single", "columnIds": [f"{p}-ld-status"], "condition": "formula",
             "formula": '[Capacity Status] = "Over capacity"',
             "style": {"backgroundColor": "#fdecea", "color": "#b3261e"}},
            {"type": "single", "columnIds": [f"{p}-ld-status"], "condition": "formula",
             "formula": '[Capacity Status] = "Within capacity"',
             "style": {"backgroundColor": "#e6f4ea", "color": "#0e7c37"}},
        ],
        "tableComponents": {"summaryBar": "hidden"},
    }

    chart = {
        "id": f"{p}-chart", "kind": "bar-chart", "name": f"Baseline vs Effective {measure_label}",
        "source": {"kind": "table", "elementId": book_id},
        "columns": [
            {"id": f"{p}-cc-dim", "name": cap_dim["name"], "formula": f"[Book/{cap_dim['name']}]"},
            {"id": f"{p}-cc-base", "name": f"Baseline {measure_label}",
             "formula": f"Sum([Book/Baseline {measure_label}])"},
            {"id": f"{p}-cc-eff", "name": f"Effective {measure_label}",
             "formula": f"Sum([Book/Effective {measure_label}])"},
        ],
        "xAxis": {"columnId": f"{p}-cc-dim"},
        "yAxis": {"columnIds": [f"{p}-cc-base", f"{p}-cc-eff"]},
        "stacking": "none", "legend": {"position": "top"},
    }

    def kpi(suffix, label, formula, source=book_id):
        return {
            "id": f"{p}-kpi-{suffix}", "kind": "kpi-chart", "name": label,
            "source": {"kind": "table", "elementId": source},
            "columns": [{"id": f"{p}-kpi-{suffix}-value", "name": label, "formula": formula,
                         "format": {"kind": "number", "formatString": ",d"}}],
            "value": {"columnId": f"{p}-kpi-{suffix}-value", "fontSize": 30},
            "style": {"backgroundColor": "#ffffff", "borderColor": "#d7dde8", "borderWidth": 1},
        }

    kpis = [
        kpi("effective", f"Effective {measure_label}", f"Sum([Book/Effective {measure_label}])"),
        kpi("baseline", f"Baseline {measure_label}", f"Sum([Book/Baseline {measure_label}])"),
        kpi("breach", f"{cap_dim['name']}s over capacity",
            f'CountDistinct(If([Capacity Load/Capacity Status] = "Over capacity", '
            f'[Capacity Load/{cap_dim["name"]}], Null))',
            source=load_id),
    ]

    btn_reset = {
        "id": f"btn-{p}-reset", "kind": "button", "text": "Clear manual overrides",
        "appearance": "filled", "align": "stretch", "fillColor": "#6c757d",
        "fontColor": "#ffffff", "fontWeight": "bold",
        "actions": [{"id": f"action-btn-{p}-reset", "trigger": "on-click", "effects": [
            {"effect": "update-rows", "tableElementId": assum_id,
             "whichRows": {"type": "formula", "formula": "True"},
             "values": {f"{p}-ia-proposed": {"type": "constant", "value": {"type": "number", "value": None}}}},
            {"effect": "set-control-value", "control": f"{p}_shift_pct",
             "value": {"type": "constant", "value": {"type": "number", "value": 0}}},
        ]}],
    }

    title = {"id": f"{p}-title", "kind": "text",
             "body": f"## **{page_name}**\nApply a bulk shift or per-row override, "
                     f"then check {cap_dim['name'].lower()}-level capacity."}

    page_id = f"page-{p}"
    data_page_id = f"page-{p}-data"
    pages = [{"id": data_page_id, "name": "Data", "visibility": "hidden"}]
    if not embed:
        pages.insert(0, {"id": page_id, "name": page_name})
    elements = [
        base,
        ctrl_shift,  # before `assum` -- see module docstring
        assum, book, load, chart, *kpis, title, btn_reset,
    ]

    content_section_xml = f"""
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="{page_id}">
  <Element elementId="{title['id']}" gridColumn="1 / 17" gridRow="1 / 4"/>
  <Element elementId="ctrl-{p}-shift" gridColumn="17 / 21" gridRow="1 / 4"/>
  <Element elementId="{btn_reset['id']}" gridColumn="21 / 25" gridRow="1 / 4"/>
  <Element elementId="{kpis[0]['id']}" gridColumn="1 / 9" gridRow="4 / 11"/>
  <Element elementId="{kpis[1]['id']}" gridColumn="9 / 17" gridRow="4 / 11"/>
  <Element elementId="{kpis[2]['id']}" gridColumn="17 / 25" gridRow="4 / 11"/>
  <Element elementId="{chart['id']}" gridColumn="1 / 25" gridRow="11 / 22"/>
  <Element elementId="{assum_id}" gridColumn="1 / 25" gridRow="22 / 40"/>
  <Element elementId="{load_id}" gridColumn="1 / 25" gridRow="40 / 52"/>
</Page>
"""
    layout_xml = f"""
{"" if embed else content_section_xml}
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="{data_page_id}">
  <Element elementId="{base_id}" gridColumn="1 / 13" gridRow="1 / 15"/>
  <Element elementId="{book_id}" gridColumn="13 / 25" gridRow="1 / 15"/>
</Page>
"""

    return {
        "elements": elements,
        "pages": pages,
        "overlays": [],
        "layout_xml": layout_xml,
        "unplaced": {
            # Only meaningful when embed=True -- lay these out inside your
            # own tab/page instead of relying on this module's own content
            # page (which isn't generated in that mode).
            "title": title["id"],
            "shift_control": f"ctrl-{p}-shift",
            "reset_button": btn_reset["id"],
            "kpi_effective": kpis[0]["id"],
            "kpi_baseline": kpis[1]["id"],
            "kpi_breach": kpis[2]["id"],
            "chart": chart["id"],
            "assumptions_table": assum_id,
            "capacity_table": load_id,
        },
        "page_id": page_id,
    }
