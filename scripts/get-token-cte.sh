#!/usr/bin/env bash
# Fork of get-token-staging.sh for the CTE Global org, which lives on Sigma's
# Canada/Azure host (api.ca.azure.sigmacomputing.com). That combined region+cloud
# hostname is not in the older allowlist, which only had api.ca. and api.az.
# Wire via SIGMA_TOKEN_FETCHER in .env.cte-global.
#
# Reads credentials from environment variables:
#   SIGMA_BASE_URL      https://api.ca.azure.sigmacomputing.com
#   SIGMA_CLIENT_ID     OAuth client ID from Sigma admin settings
#   SIGMA_CLIENT_SECRET OAuth client secret
#
# Prints:
#   export SIGMA_API_TOKEN=<token>

set -euo pipefail

: "${SIGMA_BASE_URL:?SIGMA_BASE_URL is not set}"
: "${SIGMA_CLIENT_ID:?SIGMA_CLIENT_ID is not set}"
: "${SIGMA_CLIENT_SECRET:?SIGMA_CLIENT_SECRET is not set}"

for bin in curl jq base64; do
  command -v "$bin" >/dev/null 2>&1 || { echo "Error: $bin is required" >&2; exit 1; }
done

# Pin to known Sigma cloud hosts. stdout is eval'd by the caller, so a hostile
# token-endpoint response could otherwise become RCE. Keep this an explicit
# allowlist -- never relax to a wildcard.
case "$SIGMA_BASE_URL" in
  https://aws-api.sigmacomputing.com|\
  https://api.ca.sigmacomputing.com|\
  https://api.eu.sigmacomputing.com|\
  https://api.uk.sigmacomputing.com|\
  https://api.sigmacomputing.com|\
  https://api.az.sigmacomputing.com|\
  https://api.us-a.aws.sigmacomputing.com|\
  https://api.ca.azure.sigmacomputing.com|\
  https://api.staging.sigmacomputing.io) ;;
  *) echo "Error: SIGMA_BASE_URL must be one of the published Sigma API hosts." >&2; exit 1 ;;
esac

CREDENTIALS=$(printf '%s:%s' "$SIGMA_CLIENT_ID" "$SIGMA_CLIENT_SECRET" | base64 | tr -d '\n')

RESPONSE=$(curl -sf -X POST "${SIGMA_BASE_URL}/v2/auth/token" \
  -H "Authorization: Basic ${CREDENTIALS}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials")

TOKEN=$(echo "$RESPONSE" | jq -r '.access_token')

if [[ -z "$TOKEN" || "$TOKEN" == "null" ]]; then
  echo "Error: failed to extract access_token from response:" >&2
  echo "$RESPONSE" >&2
  exit 1
fi

if ! [[ "$TOKEN" =~ ^[A-Za-z0-9._~+/=-]+$ ]]; then
  echo "Error: token contains unexpected characters; refusing to emit." >&2
  exit 1
fi

printf 'export SIGMA_API_TOKEN=%q\n' "$TOKEN"
