"""Sigma staging API helper for the JPMC code-rep build.

Reads credentials from ~/.sigma-portals/staging.env and caches the bearer token
in /tmp/.tok_staging (55-minute TTL, same convention as the other toolkits).

Verified 2026-08-07 against papercranestaging (org 8c99818a-90b3-4cae-bdb7-cf69a741171a):
  * Workbook spec bodies wrap everything except `name`/`folderId` in `document`.
  * Report spec bodies do the same, with `document.kind: report`.
"""

import base64
import json
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request

ENV_FILE = pathlib.Path.home() / ".sigma-portals" / "staging.env"
TOKEN_CACHE = pathlib.Path("/tmp/.tok_staging")
TOKEN_TTL = 55 * 60

BASE = "https://api.staging.sigmacomputing.io"
ORG_ID = "8c99818a-90b3-4cae-bdb7-cf69a741171a"

# Discovered 2026-08-07 on papercranestaging.
FOLDER_CLAUDE_BUILDER = "a758d7ee-8c23-423d-9d60-5b635d9e9b58"

# Most staging connections have disabled warehouse credentials. This one resolves
# SQL at create time (checked 2026-08-07); it is also what the reference
# "Microsoft — Executive App" workbook uses. `verify` does NOT resolve SQL, so a
# bad connection only surfaces on create.
CONN_SNOWFLAKE = "a9d45cfe-ff65-4515-8193-a7072602a1ee"


class SigmaError(RuntimeError):
    """An API call returned a non-2xx status. `body` holds the decoded payload."""

    def __init__(self, status, body, url):
        self.status = status
        self.body = body
        self.url = url
        super().__init__("HTTP %s on %s\n%s" % (status, url, body))


def _read_env():
    if not ENV_FILE.exists():
        raise SigmaError(0, "missing %s" % ENV_FILE, str(ENV_FILE))
    env = {}
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _fetch_token():
    env = _read_env()
    cid = env["SIGMA_STAGING_CLIENT_ID"]
    csec = env["SIGMA_STAGING_CLIENT_SECRET"]
    cred = base64.b64encode(("%s:%s" % (cid, csec)).encode()).decode()
    req = urllib.request.Request(
        BASE + "/v2/auth/token",
        data=urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
        headers={
            "Authorization": "Basic " + cred,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=40) as resp:
        tok = json.load(resp)["access_token"]
    TOKEN_CACHE.write_text(tok)
    os.chmod(TOKEN_CACHE, 0o600)
    return tok


def token():
    """Cached bearer token, refreshed once the cache file ages past the TTL."""
    if TOKEN_CACHE.exists() and time.time() - TOKEN_CACHE.stat().st_mtime < TOKEN_TTL:
        cached = TOKEN_CACHE.read_text().strip()
        if cached:
            return cached
    return _fetch_token()


def call(method, path, body=None, accept="application/json", retry_auth=True):
    """Issue an API call. Returns parsed JSON, or raw text when not JSON."""
    url = BASE + path
    data = None
    headers = {"Authorization": "Bearer " + token(), "Accept": accept}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            raw = resp.read().decode()
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        # A cached token can expire mid-build; refresh once and replay.
        if exc.code == 401 and retry_auth:
            _fetch_token()
            return call(method, path, body, accept, retry_auth=False)
        try:
            raw = json.dumps(json.loads(raw), indent=2)
        except ValueError:
            pass
        raise SigmaError(exc.code, raw, url) from None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return raw


# ---------------------------------------------------------------- workbooks


def verify_workbook(spec):
    return call("POST", "/v2/workbooks/spec/verify", spec)


def create_workbook(spec):
    return call("POST", "/v2/workbooks/spec", spec)


def update_workbook(workbook_id, spec):
    return call("PUT", "/v2/workbooks/%s/spec" % workbook_id, spec)


def get_workbook(workbook_id):
    return call("GET", "/v2/workbooks/%s/spec" % workbook_id)


def get_workbook_meta(workbook_id):
    # Cheap: no spec body, just latestVersion/updatedAt/updatedBy. Use this to
    # check whether someone edited the workbook since we last pushed, without
    # paying for a full spec fetch every time.
    return call("GET", "/v2/workbooks/%s" % workbook_id)


# ------------------------------------------------------------------ reports


def create_report(spec):
    return call("POST", "/v2/reports/spec", spec)


def update_report(report_id, spec):
    return call("PUT", "/v2/reports/%s/spec" % report_id, spec)


def get_report(report_id):
    return call("GET", "/v2/reports/%s/spec" % report_id)


# ------------------------------------------------------------------ plugins


def register_plugin(name, url, description=""):
    return call(
        "POST",
        "/v2/plugins",
        {"name": name, "url": url, "description": description, "type": "element"},
    )


def list_plugins():
    return call("GET", "/v2/plugins")


def describe(obj, limit=4000):
    """Pretty-print helper for poking at responses from the shell."""
    text = json.dumps(obj, indent=2) if not isinstance(obj, str) else obj
    return text[:limit]


if __name__ == "__main__":
    print("token ok, len", len(token()))
    print(describe(call("GET", "/v2/whoami")))
