"""Render a Sigma workbook or report to PNG/PDF headlessly.

This is the loop that makes a code-built dashboard self-verifying: build -> render
-> actually look at it -> fix. It uses the same async export/download pair that
already backs CSV export.

    POST {base}/v2/workbooks/{id}/export   {"format": {"type": "png"}}   -> queryId
    GET  {base}/v2/query/{queryId}/download                              -> bytes

Notes learned the hard way:
  * Poll `/v2/query/{queryId}/download`, NOT `/v2/workbooks/.../export/{queryId}`.
  * A zero-byte 200 means "not ready", not "failed" — sleep and retry.
  * Send `Accept: */*`; the payload is binary.
  * `pageId` scopes to one page, `elementId` to a single tile. PDF requires an
    elementId; PNG does not.

Usage:
    python3 shot.py workbook <workbookId> [outdir]      # every page
    python3 shot.py report   <reportId>   [outdir]
"""

import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

import sigmaapi as S

POLL_SECONDS = 3
MAX_WAIT = 180


def _req(method, path, body=None, accept="application/json"):
    url = S.BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Authorization": "Bearer " + S.token(), "Accept": accept}
    if data:
        headers["Content-Type"] = "application/json"
    return urllib.request.Request(url, data=data, headers=headers, method=method)


def start_export(kind, doc_id, fmt="png", page_id=None, element_id=None):
    body = {"format": {"type": fmt}}
    if page_id:
        body["pageId"] = page_id
    if element_id:
        body["elementId"] = element_id
    path = "/v2/%s/%s/export" % ("workbooks" if kind == "workbook" else "reports", doc_id)
    with urllib.request.urlopen(_req("POST", path, body), timeout=90) as r:
        return json.loads(r.read().decode())


def download(query_id, out_path):
    """Poll until the render is ready. Zero bytes = still rendering."""
    waited = 0
    while waited < MAX_WAIT:
        try:
            with urllib.request.urlopen(
                    _req("GET", "/v2/query/%s/download" % query_id, accept="*/*"),
                    timeout=90) as r:
                blob = r.read()
            if blob:
                pathlib.Path(out_path).write_bytes(blob)
                return len(blob)
        except urllib.error.HTTPError as exc:
            # 404/409/425 = not ready yet; 5xx = the gateway gave up waiting on a
            # render that is still running. Both are retryable.
            if exc.code not in (404, 409, 425, 500, 502, 503, 504):
                raise
        except Exception:
            pass  # transient socket/read timeout while the render is in flight
        time.sleep(POLL_SECONDS)
        waited += POLL_SECONDS
    return 0


def pages(kind, doc_id):
    path = "/v2/%s/%s/pages" % ("workbooks" if kind == "workbook" else "reports", doc_id)
    try:
        r = S.call("GET", path)
        return [(p.get("pageId") or p.get("id"), p.get("name")) for p in r.get("entries", [])]
    except S.SigmaError:
        return []


def main():
    kind = sys.argv[1]
    doc_id = sys.argv[2]
    outdir = pathlib.Path(sys.argv[3] if len(sys.argv) > 3 else "../shots")
    outdir.mkdir(parents=True, exist_ok=True)

    pgs = pages(kind, doc_id)
    print("pages:", pgs or "(none returned — exporting whole document)")

    targets = [(pid, name) for pid, name in pgs] or [(None, "all")]
    for pid, name in targets:
        slug = (name or pid or "page").lower().replace(" ", "-").replace("/", "-")
        out = outdir / ("%s-%s.png" % (kind, slug))
        try:
            job = start_export(kind, doc_id, "png", page_id=pid)
        except urllib.error.HTTPError as exc:
            print("  ✗ %-28s export failed %s %s" % (slug, exc.code, exc.read()[:160]))
            continue
        qid = job.get("queryId")
        if not qid:
            print("  ✗ %-28s no queryId in %s" % (slug, job))
            continue
        n = download(qid, out)
        print("  %s %-28s %s" % ("✓" if n else "✗", slug, ("%d bytes -> %s" % (n, out)) if n else "timed out"))


if __name__ == "__main__":
    main()
