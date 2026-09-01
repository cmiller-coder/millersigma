#!/usr/bin/env bash
# Surgically patch one (or a few) elements in an EXISTING live workbook,
# instead of regenerating and re-POSTing the whole spec for a small tweak.
#
# Sigma has no true partial-PATCH endpoint -- PUT still needs the full spec.
# This script does the GET -> merge -> sanitize -> validate -> PUT round trip
# so a small change costs one call, not re-running a 300+ line generator and
# re-reading its whole output.
#
# Usage:
#   scripts/api/patch-element.sh <workbook-id> <element-id> '<json-patch>' [<element-id2> '<json-patch2>' ...]
#
# A patch is deep-merged into the matching element (dicts merge recursively,
# lists/scalars replace outright, `null` deletes a key). Example -- change a
# KPI card's title and font size:
#   scripts/api/patch-element.sh 2BtuUrMDKEQHLrkehiSICv k-govc \
#     '{"name":{"text":"MARKETPLACE GOV (NEW)","fontSize":17}}'
#
# Before the PUT, scripts/patch_element.py runs 6 sanitize passes across the
# WHOLE spec (not just the patched element) -- see that file's docstring for
# why: PUT re-validates everything, so an unrelated pre-existing issue
# anywhere else in the workbook blocks this patch too. Sanitize notes print
# to stderr so you can see what it touched.
#
# Exits non-zero (from validate-spec.py or the PUT itself) if something's
# still broken after sanitizing -- read the message, it's a real API error at
# that point, not a masked one.
set -euo pipefail
source "$(dirname "$0")/_env.sh"

wb_id="${1:?usage: patch-element.sh <workbook-id> <element-id> '<json-patch>' [...]}"
shift
if [ "$#" -eq 0 ] || [ $(( $# % 2 )) -ne 0 ]; then
  echo "usage: patch-element.sh <workbook-id> <element-id> '<json-patch>' [<element-id2> '<json-patch2>' ...]" >&2
  exit 2
fi

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
tmp_spec="$(mktemp /tmp/patch-element.XXXXXX.json)"
trap 'rm -f "$tmp_spec"' EXIT

sigma_curl "$SIGMA_BASE_URL/v2/workbooks/$wb_id/spec" \
  | python3 "$repo_root/scripts/patch_element.py" "$@" \
  > "$tmp_spec"

"$repo_root/scripts/api/publish-workbook.sh" update "$wb_id" "$tmp_spec"
