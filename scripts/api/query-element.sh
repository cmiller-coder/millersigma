#!/usr/bin/env bash
# Fetch the rendered data behind a published workbook element as CSV (or JSON).
# Wraps Sigma's async export: POST /v2/workbooks/{wb}/export, then poll/download
# /v2/query/{queryId}/download. Output goes to stdout — pipe to python3/awk/jq.
#
# Usage:
#   scripts/api/query-element.sh <workbookId> <elementId> [format] [maxWaitSec]
#
# format defaults to "csv". Other accepted by Sigma: "json".
# maxWaitSec defaults to 60 (poll every 1s).
#
# Examples:
#   scripts/api/query-element.sh fb863946-...-7b35218b5c chart-monthly-revenue
#   scripts/api/query-element.sh <wb> kpi-revenue json | jq .
set -euo pipefail
source "$(dirname "$0")/_env.sh"

wb_id="${1:?usage: query-element.sh <workbookId> <elementId> [format] [maxWaitSec]}"
el_id="${2:?usage: query-element.sh <workbookId> <elementId> [format] [maxWaitSec]}"
fmt="${3:-csv}"
max_wait="${4:-60}"

body=$(printf '{"elementId":%s,"format":{"type":%s}}' \
  "\"$el_id\"" "\"$fmt\"")

resp=$(sigma_curl -X POST -H "Content-Type: application/json" \
  --data "$body" \
  "$SIGMA_BASE_URL/v2/workbooks/$wb_id/export")

query_id=$(printf '%s' "$resp" | python3 -c 'import sys,json; print(json.load(sys.stdin)["queryId"])')

# Poll for completion. Sigma's download endpoint streams the result when ready;
# if the job isn't done yet it returns a status JSON. Loop until we get non-JSON
# (csv) or jobComplete=true (json mode).
waited=0
while :; do
  out=$(sigma_curl "$SIGMA_BASE_URL/v2/query/$query_id/download")
  # Quick check: does it look like a status payload vs. real data?
  # (bash substring, not a `head -c 1` pipe — piping $out through head SIGPIPEs
  # printf on any response over a few KB under `set -o pipefail`.)
  first_char="${out:0:1}"
  if [ "$fmt" = "csv" ]; then
    # CSV starts with column name (alpha or quoted). Status JSON starts with '{'.
    # Empty response = job not done yet.
    if [ -n "$out" ] && [ "$first_char" != "{" ]; then
      printf '%s' "$out"
      exit 0
    fi
  else
    # JSON mode: look for "jobComplete":true OR an array start
    if printf '%s' "$out" | python3 -c 'import sys,json
d = json.load(sys.stdin)
sys.exit(0 if (isinstance(d, list) or d.get("jobComplete") is True) else 1)' 2>/dev/null; then
      printf '%s' "$out"
      exit 0
    fi
  fi
  waited=$((waited + 1))
  if [ "$waited" -ge "$max_wait" ]; then
    echo "query-element: timed out after ${max_wait}s (queryId=$query_id)" >&2
    exit 1
  fi
  sleep 1
done
