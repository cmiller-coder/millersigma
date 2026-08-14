#!/usr/bin/env python3
"""Register a custom Sigma plugin in YOUR org and print its pluginId.

A Sigma plugin is NOT built by a workbook — you host it at a URL and register it
once per org, then embed the returned pluginId in your workbook spec.

Usage:
  python3 register_plugin.py <SIGMA_BASE_URL> <TOKEN> "<name>" "<hosted-url>" ["description"]

Example (plugin served locally):
  python3 -m http.server 8080          # run inside the plugins/ folder, in another shell
  python3 register_plugin.py https://api.sigmacomputing.io "$TOKEN" \
      "Day-part Heatmap" "http://localhost:8080/cava-daypart/"

Prints the pluginId. Set it for the generator, e.g.:
  export DAYPART_PLUGIN_ID=<printed-id>
Then embed: {"kind":"plugin","pluginId":"<id>","config":{"source":{"kind":"element","elementId":"<el>"}, "<var>":"<columnId>"}}
(bindings are bare columnId strings; keys match the plugin's configureEditorPanel names).

List existing plugins:  GET /v2/plugins
"""
import sys, json, urllib.request, urllib.error

def main():
    if len(sys.argv) < 5:
        print(__doc__); sys.exit(1)
    base, tok, name, url = sys.argv[1:5]
    desc = sys.argv[5] if len(sys.argv) > 5 else name
    # Current production schema accepts name/description/url/devUrl. Older
    # helpers sent `type: element`; the current OpenAPI no longer models it.
    # Use the hosted asset in both modes by default. Leaving devUrl omitted
    # makes Sigma default to localhost:5173; author/edit mode then renders an
    # unreachable iframe for every remote user.
    body = json.dumps({
        "name": name, "description": desc, "url": url, "devUrl": url
    }).encode()
    req = urllib.request.Request(base.rstrip("/") + "/v2/plugins", data=body,
        headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"}, method="POST")
    try:
        res = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
        print(res.get("pluginId") or res)
    except urllib.error.HTTPError as e:
        msg = e.read().decode()
        # Observed on demeng production 2026-08-13: POST performs the create
        # successfully, then responds with a masked 404. Recover by listing and
        # matching the exact name + immutable production URL.
        if e.code == 404:
            try:
                req = urllib.request.Request(
                    base.rstrip("/") + "/v2/plugins?limit=1000",
                    headers={"Authorization": f"Bearer {tok}"},
                )
                entries = json.loads(
                    urllib.request.urlopen(req, timeout=30).read().decode()
                ).get("entries", [])
                matches = [
                    p for p in entries
                    if p.get("name") == name and p.get("url") == url
                ]
                if matches:
                    print(matches[-1]["pluginId"])
                    print(
                        "warning: plugin create returned masked HTTP 404, "
                        "but exact registration exists",
                        file=sys.stderr,
                    )
                    return
            except Exception:
                pass
        print(f"registration failed: HTTP {e.code}: {msg[:400]}", file=sys.stderr)
        if e.code in (401, 403):
            print("  -> your token/role may not permit plugin registration; an org admin may need to do it.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
