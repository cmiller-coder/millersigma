"""Append a notifications centre to the LIVE SoFi workbook, additively.

This does NOT regenerate the workbook from build_sofi.py. Connor built the page
header in the UI and `panels` does not round-trip through the spec API, so a
full regenerate would silently destroy it. Instead: GET the live spec, append
elements + layout, PUT it back. Everything already on the page is preserved
byte-for-byte.

Cards are one-per-row with MaxIf-filtered formulas rather than a
`repeated-container`. Repeated containers still expose no `name` field in the
OpenAPI, so the repeater-qualified `{{[Name/Column]}}` reference their own docs
require cannot be written from code -- the same reason the product cards are
built this way.

    python3 add_notifications.py [--dry]
"""

import json
import pathlib
import sys

import brand as B
import sigmaapi as S

WORKBOOK = "8f10c147-da2e-4e45-ba0c-b51934255571"
SQL = pathlib.Path(__file__).resolve().parent.parent / "sql"
NT = "Notifications"

# lucide-style glyphs, stroked in the severity colour
ICON_ALERT = ('<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/>'
              '<line x1="12" y1="16" x2="12.01" y2="16"/>')
ICON_WARN = ('<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86'
             'a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/>'
             '<line x1="12" y1="17" x2="12.01" y2="17"/>')
ICON_INFO = ('<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/>'
             '<line x1="12" y1="8" x2="12.01" y2="8"/>')
ICON_BELL = ('<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>'
             '<path d="M13.73 21a2 2 0 0 1-3.46 0"/>')

SEV = {
    "critical": (B.BAD, ICON_ALERT, "#FEF2F2", "#FCA5A5"),
    "warning":  (B.WARN, ICON_WARN, "#FFFBEB", "#FCD34D"),
    "info":     (B.SOFI_BRIGHT, ICON_INFO, "#EFF6FF", "#93C5FD"),
}

# (alert order, severity) -- must match notifications.sql
ALERTS = [(1, "critical"), (2, "critical"), (3, "warning"),
          (4, "warning"), (5, "info"), (6, "info")]

new_elements = []


def add(el):
    new_elements.append(el)


def one(col, order):
    """The single-row read. MaxIf over a one-row match is how every card in this
    workbook pulls its own value without a repeated container."""
    return 'MaxIf([%s/%s], [%s/Alert Order] = %d)' % (NT, col, NT, order)


add({"id": "tbl-notif", "kind": "table", "name": NT, "visibleAsSource": True,
     "source": {"connectionId": S.CONN_SNOWFLAKE, "kind": "sql",
                "statement": (SQL / "notifications.sql").read_text()},
     "columns": [{"id": "n%d" % i, "formula": "[Custom SQL/%s]" % c, "name": c}
                 for i, c in enumerate(["Alert Order", "Severity", "Title",
                                        "Body", "Age", "Owner"])]})

# section marker
add({"id": "c-secn", "kind": "container",
     "style": {"backgroundColor": "transparent", "padding": "none"}})
add({"id": "ico-notif", "kind": "image",
     "source": {"kind": "url", "url": B.icon(ICON_BELL)},
     "style": {"fit": "contain", "backgroundColor": "transparent", "padding": "none"}})
add({"id": "notif-heading", "kind": "text",
     "body": '<span style="color: %s">**NOTIFICATION CENTER**</span>' % B.SOFI_BRIGHT,
     "style": {"backgroundColor": "transparent", "padding": "none"},
     "verticalAlign": "middle"})

for order, sev in ALERTS:
    colour, glyph, tint, border = SEV[sev]
    k = "n%d" % order
    add({"id": "ncard-%s" % k, "kind": "container",
         # borderWidth/borderColor require default padding -- setting
         # padding:"none" alongside them is a hard rejection
         "style": {"backgroundColor": tint, "borderRadius": "round",
                   "borderColor": border, "borderWidth": 1}})
    add({"id": "nico-%s" % k, "kind": "image",
         "source": {"kind": "url", "url": B.icon(glyph, colour, 24)},
         "style": {"fit": "contain", "align": "start",
                   "backgroundColor": "transparent", "padding": "none"}})
    add({"id": "ntitle-%s" % k, "kind": "text",
         "body": '<span style="color: %s">**{{%s}}**</span>' % (colour, one("Title", order)),
         "style": {"backgroundColor": "transparent", "padding": "none"},
         "verticalAlign": "middle"})
    add({"id": "nbody-%s" % k, "kind": "text",
         "body": '<span style="color: %s">{{%s}}</span>' % (B.TEXT_DARK, one("Body", order)),
         "style": {"backgroundColor": "transparent", "padding": "none"},
         "verticalAlign": "start"})
    add({"id": "nmeta-%s" % k, "kind": "text",
         "body": '<span style="color: %s">{{%s}} · {{%s}}</span>'
                 % (B.TEXT_MUTED, one("Owner", order), one("Age", order)),
         "style": {"backgroundColor": "transparent", "padding": "none"},
         "verticalAlign": "end"})


def card_layout(order, top):
    k = "n%d" % order
    return (
        '  <Container elementId="ncard-%s" type="grid" gridColumn="%d / %d" gridRow="%d / %d" '
        'gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">\n'
        '    <Element elementId="nico-%s" gridColumn="1 / 2" gridRow="1 / 3"/>\n'
        '    <Element elementId="ntitle-%s" gridColumn="2 / 13" gridRow="1 / 3"/>\n'
        '    <Element elementId="nbody-%s" gridColumn="2 / 13" gridRow="3 / 6"/>\n'
        '    <Element elementId="nmeta-%s" gridColumn="2 / 13" gridRow="6 / 8"/>\n'
        '  </Container>' % (k, 1 + ((order - 1) % 3) * 8, 9 + ((order - 1) % 3) * 8,
                            top, top + 9, k, k, k, k))


def main():
    doc = S.call("GET", "/v2/workbooks/%s/spec" % WORKBOOK)["document"]
    have = {e["id"] for e in doc["elements"]}
    clash = have & {e["id"] for e in new_elements}
    if clash:
        raise SystemExit("id clash with live workbook: %s" % sorted(clash))

    layout = doc["layout"]
    # find the last row used on pg1 so the new band lands underneath everything
    i = layout.index('id="pg1"')
    j = layout.index("</Page>", i)
    pg1 = layout[i:j]
    import re
    last = 0
    for m in re.finditer(r'gridRow="\d+ / (\d+)"', pg1):
        last = max(last, int(m.group(1)))
    top = last + 1

    block = ('  <Container elementId="c-secn" type="grid" gridColumn="1 / 25" gridRow="%d / %d" '
             'gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">\n'
             '    <Element elementId="ico-notif" gridColumn="1 / 2" gridRow="1 / 3"/>\n'
             '    <Element elementId="notif-heading" gridColumn="2 / 25" gridRow="1 / 3"/>\n'
             '  </Container>\n' % (top, top + 3))
    rows = [card_layout(o, top + 3 + (idx // 3) * 10)
            for idx, (o, _s) in enumerate(ALERTS)]
    block += "\n".join(rows) + "\n"

    doc["elements"] = doc["elements"] + new_elements
    layout = layout[:j] + block + layout[j:]

    # the source table itself needs a slot; it lives on the hidden Data page
    dp = layout.index('id="pgData"')
    de = layout.index("</Page>", dp)
    dlast = 0
    for m in re.finditer(r'gridRow="\d+ / (\d+)"', layout[dp:de]):
        dlast = max(dlast, int(m.group(1)))
    layout = (layout[:de]
              + '  <Element elementId="tbl-notif" gridColumn="1 / 9" gridRow="%d / %d"/>\n'
                % (dlast + 1, dlast + 13)
              + layout[de:])
    doc["layout"] = layout

    if "--dry" in sys.argv:
        pathlib.Path("/tmp/notif-preview.xml").write_text(doc["layout"])
        print("dry run — %d new elements, band starts at row %d" % (len(new_elements), top))
        return
    S.update_workbook(WORKBOOK, {"document": doc})
    print("✅ appended %d elements; notification centre at row %d" % (len(new_elements), top))


if __name__ == "__main__":
    main()
