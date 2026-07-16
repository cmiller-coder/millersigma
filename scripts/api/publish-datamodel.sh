#!/usr/bin/env bash
# Publish data model specs to Sigma — POST a new data model, PUT an update to
# an existing one, GET the spec back. Mirrors publish-workbook.sh; there is
# no upstream sigma-data-models wrapper for this in this environment, so this
# is a project-local equivalent for the CREATE/UPDATE/GET round-trip.
#
# Usage:
#   scripts/api/publish-datamodel.sh post <spec-file>
#   scripts/api/publish-datamodel.sh put  <dataModelId> <spec-file>
#   scripts/api/publish-datamodel.sh get-spec <dataModelId>
#
# Auth, Accept: application/json header, and 401 auto-retry are all handled
# by the sigma_curl helper in _env.sh. No `delete` subcommand — deletion
# stays on the direct-curl path so it always hits the DELETE ask pattern in
# .claude/settings.json.
set -euo pipefail
source "$(dirname "$0")/_env.sh"

cmd="${1:-}"
case "$cmd" in
  post)
    spec="${2:?usage: publish-datamodel.sh post <spec-file>}"
    if [ ! -f "$spec" ]; then
      echo "publish-datamodel: spec file not found: $spec" >&2
      exit 2
    fi
    sigma_curl -X POST \
      -H "Content-Type: application/json" \
      --data-binary "@$spec" \
      "$SIGMA_BASE_URL/v2/dataModels/spec"
    ;;
  put)
    dm_id="${2:?usage: publish-datamodel.sh put <dataModelId> <spec-file>}"
    spec="${3:?usage: publish-datamodel.sh put <dataModelId> <spec-file>}"
    if [ ! -f "$spec" ]; then
      echo "publish-datamodel: spec file not found: $spec" >&2
      exit 2
    fi
    sigma_curl -X PUT \
      -H "Content-Type: application/json" \
      --data-binary "@$spec" \
      "$SIGMA_BASE_URL/v2/dataModels/$dm_id/spec"
    ;;
  get-spec)
    dm_id="${2:?usage: publish-datamodel.sh get-spec <dataModelId>}"
    sigma_curl "$SIGMA_BASE_URL/v2/dataModels/$dm_id/spec"
    ;;
  *)
    cat >&2 <<'USAGE'
usage:
  publish-datamodel.sh post     <spec-file>
  publish-datamodel.sh put      <dataModelId> <spec-file>
  publish-datamodel.sh get-spec <dataModelId>
USAGE
    exit 2
    ;;
esac
