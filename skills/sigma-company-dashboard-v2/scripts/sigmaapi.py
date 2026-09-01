"""Sigma API helper — shells out to the sigma CLI (~/.sigma-cli/bin/sigma) for
every endpoint it exposes. The CLI owns auth entirely: no ~/.sigma-portals env
file, no /tmp token cache, no manual TTL. `sigma auth token`/`auth status` are
the only auth primitives this module touches, and the token is cached only for
the lifetime of this process (a module-level variable, not on disk) — the CLI
handles refresh on the next process.

Two endpoint families have NO CLI coverage as of the sigma-cli build checked
2026-08-25 (confirmed via `sigma api list-prefixes --refresh-spec`, not a stale
cache): report-as-code (`/v2/reports/spec`) and plugin registration
(`/v2/plugins`). Those five functions (create_report/update_report/get_report/
register_plugin/list_plugins) fall back to a direct HTTP call, still sourcing
their bearer token from `sigma auth token` — see `_raw_call`. Drop this
fallback once the CLI adds those endpoints.
"""

import json
import re
import subprocess
import pathlib
import os
import urllib.error
import urllib.request

CLI = pathlib.Path(os.environ.get("SIGMA_CLI_BIN")
                    or (pathlib.Path.home() / ".sigma-cli" / "bin" / "sigma"))
PROFILE = os.environ.get("SIGMA_CLI_PROFILE", "papercranestaging")

# These three are org-specific and MUST be overridden via .env for any org
# other than Connor's own papercranestaging (never commit real values for a
# different org into these fallbacks — .env is gitignored, this file is not).
ORG_ID = os.environ.get("SIGMA_ORG_ID", "8c99818a-90b3-4cae-bdb7-cf69a741171a")

# Discovered 2026-08-07 on papercranestaging.
FOLDER_CLAUDE_BUILDER = os.environ.get("SIGMA_FOLDER_ID", "a758d7ee-8c23-423d-9d60-5b635d9e9b58")

# Most staging connections have disabled warehouse credentials. This one resolves
# SQL at create time; it is also what the reference "Microsoft — Executive App"
# workbook uses. `verify` does NOT resolve SQL, so a bad connection only surfaces
# on create.
CONN_SNOWFLAKE = os.environ.get("SIGMA_CONNECTION_ID", "a9d45cfe-ff65-4515-8193-a7072602a1ee")


class SigmaError(RuntimeError):
    """Base for every error this module raises. `body` holds the raw JSON text
    the CLI (or, for the two unsupported endpoint families, the HTTP response)
    printed — existing call sites do `json.loads(exc.body)`, so this stays a
    string, not a parsed dict."""

    def __init__(self, status, body, url):
        self.status = status
        self.body = body
        self.url = url
        super().__init__("HTTP %s on %s\n%s" % (status, url, body))


class SigmaAPIError(SigmaError):
    """CLI exit 1 — Sigma returned an error response."""


class SigmaAuthError(SigmaError):
    """CLI exit 2 — credentials missing or invalid (or the CLI itself is
    missing/unauthenticated — see _require_cli / _api_host)."""


class SigmaValidationError(SigmaError):
    """CLI exit 3 — bad arguments/input (includes our own malformed --json)."""


class SigmaNetworkError(SigmaError):
    """CLI exit 4 — transport/DNS failure."""


_EXIT_ERRORS = {1: SigmaAPIError, 2: SigmaAuthError,
                3: SigmaValidationError, 4: SigmaNetworkError}


def _status_from_body(text, exit_code):
    """CLI API-error bodies carry a real HTTP `code`; the other exit codes
    don't map to one, so synthesize something call sites can still branch on."""
    try:
        code = json.loads(text).get("code")
        if isinstance(code, int):
            return code
    except (ValueError, AttributeError, TypeError):
        pass
    return {2: 401, 3: 400, 4: 599}.get(exit_code, 500)


def _require_cli():
    if not CLI.exists():
        raise SigmaAuthError(
            0, "sigma CLI not found at %s (set SIGMA_CLI_BIN to override)" % CLI,
            str(CLI))


def _run(args, url_for_error):
    """Run `sigma -p PROFILE api <args>`; return parsed stdout JSON on success."""
    _require_cli()
    proc = subprocess.run([str(CLI), "-p", PROFILE, "api", *args],
                           capture_output=True, text=True, timeout=180)
    if proc.returncode != 0:
        err_cls = _EXIT_ERRORS.get(proc.returncode, SigmaAPIError)
        raise err_cls(_status_from_body(proc.stdout, proc.returncode),
                      proc.stdout, url_for_error)
    if not proc.stdout.strip():
        return None
    return json.loads(proc.stdout)


def _j(obj):
    return json.dumps(obj)


_token_cache = None


def token():
    """Bearer token from the CLI, cached in memory for this process only — no
    disk cache, no TTL. Shelling out per call is too many subprocesses for a
    build that fires dozens of requests; a stale in-process token just means
    the *next* process re-fetches, which the CLI already handles."""
    global _token_cache
    if _token_cache is None:
        _require_cli()
        proc = subprocess.run([str(CLI), "-p", PROFILE, "auth", "token"],
                              capture_output=True, text=True, timeout=40)
        if proc.returncode != 0:
            raise SigmaAuthError(401, proc.stdout or proc.stderr,
                                 "sigma auth token -p %s" % PROFILE)
        _token_cache = proc.stdout.strip()
    return _token_cache


def _api_host():
    _require_cli()
    proc = subprocess.run([str(CLI), "-p", PROFILE, "auth", "status"],
                          capture_output=True, text=True, timeout=40)
    # `auth status` writes its human-readable report to stderr, not stdout.
    combined = proc.stdout + proc.stderr
    m = re.search(r"API host:\s*(\S+)", combined)
    if proc.returncode != 0 or not m:
        raise SigmaAuthError(
            401,
            "sigma CLI profile %r is not authenticated (or is missing).\n"
            "Run: sigma auth login -p %s\n\n--- sigma auth status output ---\n%s"
            % (PROFILE, PROFILE, combined.strip()),
            "sigma auth status -p %s" % PROFILE)
    return m.group(1)


try:
    BASE = "https://" + _api_host()
except SigmaAuthError as exc:
    raise SigmaAuthError(
        exc.status,
        "sigmaapi could not initialize — sigma CLI profile %r is not ready.\n"
        "Run: sigma auth login -p %s\n\n%s" % (PROFILE, PROFILE, exc.body),
        exc.url) from None


# ---------------------------------------------------------------- workbooks


def verify_workbook(spec):
    return _run(["workbooks", "spec", "verify", "--json", _j(spec)],
                "/v2/workbooks/spec/verify")


def create_workbook(spec):
    return _run(["workbooks", "spec", "create", "--json", _j(spec)],
                "/v2/workbooks/spec")


def update_workbook(workbook_id, spec):
    return _run(["workbooks", "spec", "update",
                 "--params", _j({"workbookId": workbook_id}), "--json", _j(spec)],
                "/v2/workbooks/%s/spec" % workbook_id)


def get_workbook(workbook_id):
    return _run(["workbooks", "spec", "get",
                 "--params", _j({"workbookId": workbook_id})],
                "/v2/workbooks/%s/spec" % workbook_id)


def get_workbook_meta(workbook_id):
    # Cheap: no spec body, just latestVersion/updatedAt/updatedBy.
    return _run(["workbooks", "get", "--params", _j({"workbookId": workbook_id})],
                "/v2/workbooks/%s" % workbook_id)


# ------------------------------------------------------- generic call() shim
#
# The CLI has no arbitrary-path escape hatch (it's an OpenAPI-operation tree,
# not a raw method+path client), so this only covers the exact (method, path)
# pairs the codebase actually calls today: qa_pg1.py's clone-and-render dance,
# and shot_report.py's PDF export kickoff. Add a route here if a new one shows
# up — don't widen this into a real generic client.

def call(method, path, body=None, accept="application/json", retry_auth=True):
    m = re.match(r"^/v2/workbooks/([^/]+)/spec$", path)
    if method == "GET" and m:
        return get_workbook(m.group(1))
    if method == "POST" and path == "/v2/workbooks":
        return _run(["workbooks", "create", "--json", _j(body)], path)
    m = re.match(r"^/v2/files/([^/]+)$", path)
    if method == "DELETE" and m:
        return _run(["files", "delete", "--params", _j({"inodeId": m.group(1)})], path)
    m = re.match(r"^/v2/reports/([^/]+)/export$", path)
    if method == "POST" and m:
        return _run(["reports", "export",
                     "--params", _j({"reportId": m.group(1)}), "--json", _j(body)], path)
    raise NotImplementedError(
        "sigmaapi.call() has no CLI route for %s %s. The sigma CLI has no "
        "generic arbitrary-path escape hatch, so call() only covers the paths "
        "this codebase actually uses — add a route above." % (method, path))


# ------------------------------------------------------------------ reports
#
# No CLI coverage — /v2/reports/spec isn't in the CLI's OpenAPI surface at all
# (checked with --refresh-spec, 2026-08-25). Direct HTTP, CLI-sourced token.


def _raw_call(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Authorization": "Bearer " + token(), "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            raw = resp.read().decode()
    except urllib.error.HTTPError as exc:
        raise SigmaAPIError(exc.code, exc.read().decode(), url) from None
    except urllib.error.URLError as exc:
        raise SigmaNetworkError(0, str(exc.reason), url) from None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return raw


def create_report(spec):
    return _raw_call("POST", "/v2/reports/spec", spec)


def update_report(report_id, spec):
    return _raw_call("PUT", "/v2/reports/%s/spec" % report_id, spec)


def get_report(report_id):
    return _raw_call("GET", "/v2/reports/%s/spec" % report_id)


# ------------------------------------------------------------------ plugins
#
# No CLI coverage — no `plugins` resource exists in the CLI at all.


def register_plugin(name, url, description=""):
    return _raw_call("POST", "/v2/plugins",
                     {"name": name, "url": url, "description": description,
                      "type": "element"})


def list_plugins():
    return _raw_call("GET", "/v2/plugins")


def describe(obj, limit=4000):
    """Pretty-print helper for poking at responses from the shell."""
    text = json.dumps(obj, indent=2) if not isinstance(obj, str) else obj
    return text[:limit]


if __name__ == "__main__":
    print("token ok, len", len(token()))
    print(describe(_run(["whoami", "get"], "/v2/whoami")))
