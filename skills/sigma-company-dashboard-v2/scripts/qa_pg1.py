"""Render page 1 headlessly by cloning the workbook with its plugins stubbed out.

Page 1 carries two registered plugins that both fetch and animate (the Treasury
ticker and the balance flywheel). The headless renderer waits for the page to go
idle, and neither plugin ever does, so `pageId=pg1` times out every time. Every
OTHER page renders in ~30s.

So: clone the live spec into a throwaway workbook, replace each plugin element
with an inert text tile of the same id, render that, delete the clone. Geometry
and every non-plugin element are untouched, which is exactly what layout QA
needs to check.

    python3 qa_pg1.py [outdir]
"""

import os
import pathlib
import subprocess
import sys

import sigmaapi as S

WORKBOOK = os.environ.get("WORKBOOK", "8f10c147-da2e-4e45-ba0c-b51934255571")
STUB = ("plg-ticker", "plg-wheel")


def rotate_tabs(doc, n):
    """A tabbed container has no default-tab field, and a headless render only
    paints the ACTIVE tab -- so to see tab N we rotate the <Tab> blocks (and the
    matching `tabs` name array) until N is first."""
    if not n:
        return
    lay = doc["layout"]
    start = lay.index('<TabbedContainer elementId="tc-persona"')
    open_tag_end = lay.index(">", start) + 1
    end = lay.index("</TabbedContainer>", start)
    inner = lay[open_tag_end:end]
    parts, depth, buf = [], 0, ""
    for line in inner.splitlines(True):
        if "<Tab " in line:
            depth += 1
        buf += line
        if "</Tab>" in line:
            depth -= 1
            if depth == 0:
                parts.append(buf); buf = ""
    parts = parts[n:] + parts[:n]
    doc["layout"] = lay[:open_tag_end] + "".join(parts) + lay[end:]
    for e in doc["elements"]:
        if e["id"] == "tc-persona":
            e["tabs"] = e["tabs"][n:] + e["tabs"][:n]


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else "../shots/qa"
    tab = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    doc = S.call("GET", "/v2/workbooks/%s/spec" % WORKBOOK)["document"]
    doc["elements"] = [
        e if e["id"] not in STUB else
        {"id": e["id"], "kind": "text", "body": "**%s (stubbed for render)**" % e["id"],
         "style": {"backgroundColor": "#0B2740", "padding": "none"}}
        for e in doc["elements"]]
    rotate_tabs(doc, tab)

    clone = S.call("POST", "/v2/workbooks",
                   {"name": "ZZ qa pg1 clone", "folderId": S.FOLDER_CLAUDE_BUILDER})
    wid = clone["workbookId"]
    try:
        S.update_workbook(wid, {"document": doc})
        subprocess.run([sys.executable, "shot.py", "workbook", wid, outdir], check=False)
    finally:
        # delete by the exact tracked id -- never by name pattern, this is a
        # shared org and a wildcard delete has bitten before
        try:
            S.call("DELETE", "/v2/files/%s" % wid)
            print("cleaned up clone", wid)
        except Exception as exc:
            print("MANUAL CLEANUP NEEDED:", wid, str(exc)[:120])


if __name__ == "__main__":
    main()
