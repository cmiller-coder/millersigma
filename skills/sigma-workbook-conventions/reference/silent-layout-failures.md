# The four silent layout failures

Every one of these renders as **nothing**. No error at `verify`, no error at
`create`, no empty box, no console warning — the element simply is not there.
Together they cost more debugging time than every documented error message
combined, because the natural assumption is "my data is wrong" when the data is
fine.

Run the linter below before every push. It catches two of the four statically.

---

## 1. A container's internal rows must not exceed the span its parent gives it

The single most expensive one.

```xml
<!-- BROKEN: card needs 10 internal rows, parent grants 5 -->
<Container elementId="ncard" gridRow="9 / 14" gridTemplateRows="auto">
  <Element elementId="nico"  gridRow="1 / 3"/>
  <Element elementId="ntitle" gridRow="3 / 5"/>
  <Element elementId="nbody" gridRow="5 / 8"/>
  <Element elementId="nkpi"  gridRow="8 / 11"/>   <!-- needs 10 rows -->
</Container>
```

The container is allotted less height than its children need and collapses to
zero. Either widen the parent span or compress the children — the rule is
`max(child end row) - 1 <= (parent end - parent start)`.

## 2. `text` has no `source`, so `{{...}}` only resolves next to a sourced element

A `text` element's field list is `body, id, kind, overflow, verticalAlign`.
There is no `source`. A dynamic-text formula inside one resolves against **a
sourced data element sharing its container** — with none present the formula
returns empty, and if every child is empty the container collapses (see #1).

```json
{"id": "card", "kind": "container"}
{"id": "t", "kind": "text", "body": "{{MaxIf([T/Title], [T/Key] = \"a1\")}}"}
{"id": "k", "kind": "kpi-chart", "source": {"elementId": "tbl", "kind": "table"},
 "columns": [{"id": "kv", "formula": "MaxIf([T/Impact], [T/Key] = \"a1\")"}]}
```

That `kpi-chart` is not decoration — it is what makes the text bind. Give it a
metric worth showing and the constraint pays for itself.

## 3. Overlapping siblings drop silently

Two elements overlapping in the same grid scope does **not** raise. One of them
vanishes, and which one is not predictable. `create` reports
`Element collisions found during layout edit` only sometimes.

## 4. `1fr` row tracks collapse inside an auto-height `<Tab>`

`gridTemplateRows="repeat(12, 1fr)"` needs a definite parent height. A `<Tab>`
is auto-height, so the tracks resolve to zero and every child disappears. Use
`gridTemplateRows="auto"` inside tabs.

---

## The linter

Walks the generated XML and reports #1 and #3 before you push. Wire it into the
build so it runs on every generate.

```python
import xml.etree.ElementTree as ET

def lint(layout_xml):
    root = ET.fromstring("<root>" + layout_xml.split("?>", 1)[1] + "</root>")
    issues = 0

    def rect(e):
        c, r = e.get("gridColumn"), e.get("gridRow")
        if not c or not r:
            return None
        cs, ce = [int(v) for v in c.split("/")]
        rs, re_ = [int(v) for v in r.split("/")]
        return cs, ce, rs, re_

    def walk(node, path):
        nonlocal issues
        kids = [(rect(k), k.get("elementId") or k.tag, k)
                for k in list(node) if rect(k)]
        for i in range(len(kids)):
            for j in range(i + 1, len(kids)):
                (c1, e1, r1, x1), n1, _ = kids[i]
                (c2, e2, r2, x2), n2, _ = kids[j]
                if c1 < e2 and c2 < e1 and r1 < x2 and r2 < x1:
                    print("COLLISION", path, ":", n1, "x", n2)
                    issues += 1
        for (c, e, r, x), n, k in kids:
            inner = [rect(gc)[3] for gc in list(k) if rect(gc)]
            if inner and max(inner) - 1 > (x - r):
                print("OVERFLOW", path, "/", n,
                      ": needs", max(inner) - 1, "rows, has", x - r)
                issues += 1
        for k in list(node):
            walk(k, path + "/" + (k.get("id") or k.get("elementId") or k.tag))

    walk(root, "")
    return issues
```

---

## Related traps that DO error, but misleadingly

| Symptom | Cause |
| --- | --- |
| `Invalid kind: "button"` | An unrecognised **field** on the element, not a bad kind. Most often an effect the deployed API doesn't support. |
| Masked 500 on `PUT` | An unrecognised layout XML **tag**, or an unsubstituted `__PLACEHOLDER__` left in the XML. |
| `verify` passes, `create` fails | `verify` skips SQL resolution, dangling ids, duplicate ids and workspace feature flags. **Never trust `verify` alone.** |
| Overlay renders "New Modal" | `header.title` omitted. An empty string `""` **crashes** the overlay; a single space `" "` gives a blank bar. The header cannot be hidden — the schema exposes only `title` and `showCloseIcon`. |
