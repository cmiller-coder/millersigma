"""Find the reference syntax that binds a repeated-container child to its card row.

A write succeeding proves nothing here — `{{[Product]}}` writes clean and still
fails at query time — so every candidate is CREATED and then RENDERED, and the
PNG is what scores it.

Strategy: validate each candidate on its own with a cheap create (fast), then
assemble the survivors into ONE workbook so a single ~30s render scores them all.

    python3 rc_matrix.py
"""

import json
import pathlib
import sys

import sigmaapi as S
import shot

SRC_SQL = ("SELECT 'Personal Loans' AS \"Product\", 18.42 AS \"Bal\" "
           "UNION ALL SELECT 'Credit Card', 1.28")
SRC_NAME = "Product Source"


def src_table(eid="src"):
    return {"id": eid, "kind": "table", "name": SRC_NAME,
            "source": {"connectionId": S.CONN_SNOWFLAKE, "kind": "sql",
                       "statement": SRC_SQL},
            "columns": [{"id": "c0", "formula": "[Custom SQL/Product]", "name": "Product"},
                        {"id": "c1", "formula": "[Custom SQL/Bal]", "name": "Bal"}]}


def txt(eid, body, **extra):
    e = {"id": eid, "kind": "text", "body": body}
    e.update(extra)
    return e


# Each candidate: (key, human label, repeater dict, [child elements])
# `rc` id and child ids get suffixed per candidate by build().
def candidates():
    out = []

    def rc(**extra):
        base = {"kind": "repeated-container",
                "source": {"elementId": "src", "kind": "table"}}
        base.update(extra)
        return base

    out.append(("bare", "{{[Product]}}", rc(),
                [txt("k", "**{{[Product]}}**")]))
    out.append(("nobrk", "{{Product}}", rc(),
                [txt("k", "**{{Product}}**")]))
    out.append(("srcname", "{{[Product Source/Product]}}", rc(),
                [txt("k", "**{{[Product Source/Product]}}**")]))
    out.append(("selfrow", "{{[Selection/Product]}}", rc(),
                [txt("k", "**{{[Selection/Product]}}**")]))
    out.append(("thisrow", "{{[Row/Product]}}", rc(),
                [txt("k", "**{{[Row/Product]}}**")]))
    # child carries its own source pointing at the repeater
    out.append(("childsrc_rc", "child source -> repeater", rc(),
                [txt("k", "**{{[Product]}}**",
                     source={"elementId": "RC", "kind": "table"})]))
    # child source -> the underlying table
    out.append(("childsrc_tbl", "child source -> source table", rc(),
                [txt("k", "**{{[Product Source/Product]}}**",
                     source={"elementId": "src", "kind": "table"})]))
    # repeater sourced directly from SQL rather than another element
    out.append(("directsql", "repeater sourced from SQL",
                {"kind": "repeated-container",
                 "source": {"connectionId": S.CONN_SNOWFLAKE, "kind": "sql",
                            "statement": SRC_SQL},
                 "columns": [{"id": "d0", "formula": "[Custom SQL/Product]", "name": "Product"}]},
                [txt("k", "**{{[Product]}}**")]))
    # a data element as the card child (official doc says rejected — verify)
    out.append(("kpi", "kpi-chart child", rc(),
                [{"id": "k", "kind": "kpi-chart",
                  "source": {"elementId": "src", "kind": "table"},
                  "columns": [{"id": "kv", "formula": "[Product Source/Bal]", "name": "Bal"}],
                  "value": {"columnId": "kv"},
                  "name": {"visibility": "hidden"}}]))
    out.append(("table", "table child", rc(),
                [{"id": "k", "kind": "table",
                  "source": {"elementId": "src", "kind": "table"},
                  "columns": [{"id": "tv", "formula": "[Product Source/Product]",
                               "name": "Product"}]}]))
    return out


def suffix(obj, sfx, rc_id):
    """Rewrite ids/references for one candidate instance."""
    s = json.dumps(obj)
    s = s.replace('"RC"', '"%s"' % rc_id)
    return json.loads(s)


def build_one(key, rc_def, children):
    rc_id = "rc_" + key
    els = []
    r = dict(rc_def)
    r["id"] = rc_id
    els.append(suffix(r, key, rc_id))
    child_ids = []
    for ch in children:
        c = dict(ch)
        c["id"] = "%s_%s" % (ch["id"], key)
        child_ids.append(c["id"])
        els.append(suffix(c, key, rc_id))
    return rc_id, child_ids, els


def page_layout(blocks):
    """blocks = [(label_id, rc_id, [child_ids])] stacked vertically."""
    xml = ['<?xml version="1.0" encoding="utf-8"?>',
           '<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg1">',
           '  <Element elementId="src" gridColumn="1 / 25" gridRow="1 / 4"/>']
    row = 4
    for label_id, rc_id, child_ids in blocks:
        xml.append('  <Element elementId="%s" gridColumn="1 / 25" gridRow="%d / %d"/>'
                   % (label_id, row, row + 2))
        row += 2
        xml.append('  <Container elementId="%s" type="grid" gridColumn="1 / 25" gridRow="%d / %d" '
                   'gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">' % (rc_id, row, row + 6))
        for i, cid in enumerate(child_ids):
            xml.append('    <Element elementId="%s" gridColumn="1 / 13" gridRow="%d / %d"/>'
                       % (cid, i * 2 + 1, i * 2 + 3))
        xml.append('  </Container>')
        row += 7
    xml.append('</Page>')
    return "\n".join(xml)


def try_create(name, elements, layout):
    doc = {"schemaVersion": 1, "kind": "workbook", "elements": elements,
           "pages": [{"id": "pg1", "name": "P"}], "layout": layout}
    return S.create_workbook({"name": name, "folderId": S.FOLDER_CLAUDE_BUILDER,
                              "document": doc})


def main():
    survivors = []
    print("=== step 1: which candidates even write? ===")
    for key, label, rc_def, children in candidates():
        rc_id, child_ids, els = build_one(key, rc_def, children)
        lbl = txt("lbl_" + key, "`%s`" % label)
        elements = [src_table(), lbl] + els
        layout = page_layout([("lbl_" + key, rc_id, child_ids)])
        try:
            r = try_create("ZZ rcm " + key, elements, layout)
            S.call("DELETE", "/v2/files/%s" % r["workbookId"])
            print("  ✅ %-14s %s" % (key, label))
            survivors.append((key, label, rc_def, children))
        except S.SigmaError as exc:
            m = exc.body
            try:
                m = json.loads(exc.body).get("message", m)
            except ValueError:
                pass
            print("  ❌ %-14s %-34s %s" % (key, label, m[:90]))

    if not survivors:
        print("\nno candidate writes — nothing to render")
        return

    print("\n=== step 2: one workbook with %d survivors, single render ===" % len(survivors))
    elements = [src_table()]
    blocks = []
    for key, label, rc_def, children in survivors:
        rc_id, child_ids, els = build_one(key, rc_def, children)
        elements.append(txt("lbl_" + key, "**`%s`** — %s" % (key, label)))
        elements.extend(els)
        blocks.append(("lbl_" + key, rc_id, child_ids))
    layout = page_layout(blocks)
    r = try_create("ZZ rc matrix", elements, layout)
    wid = r["workbookId"]
    print("  workbook:", wid)
    shot.MAX_WAIT = 300
    job = shot.start_export("workbook", wid, "png", page_id="pg1")
    out = pathlib.Path("../shots/rc-matrix.png")
    n = shot.download(job["queryId"], out)
    print("  render:", n, "bytes ->", out)
    pathlib.Path("/tmp/rc_matrix_wid.txt").write_text(wid)


if __name__ == "__main__":
    main()
