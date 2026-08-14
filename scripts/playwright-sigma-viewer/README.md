# Playwright Sigma viewer

Real, authenticated browser eyes on a live Sigma workbook -- for catching
things the API-based headless export pipeline (`qa_pg1.py`/`shot.py`) can
miss (e.g. the KPI-card opaque-white-instead-of-transparent bug, only
visible in an actual rendered session).

Claude-in-Chrome (the MCP browser extension) is the normal path for this.
This directory exists as a fallback for when that extension isn't
connected/available -- a real headless Playwright browser, not a fake one.

## Setup (one-time, browsers already cached under `~/Library/Caches/ms-playwright/`)

```bash
cd ~/Desktop/millersigma/scripts/playwright-sigma-viewer
npm install
```

## Auth

Sigma staging requires a real login (SSO/Okta) -- there is no way around
this with an API bearer token, and passwords must never be entered by
Claude on the user's behalf. Instead:

```bash
node login-and-save.js
```

This opens a REAL (non-headless) browser window. The user logs in
themselves (SSO/MFA is fine). Once landed back on
`staging.sigmacomputing.io` (not still on the Okta domain), it saves
cookies + localStorage to `session.json`.

**`session.json` is gitignored on purpose** -- it's a live session, not a
credential to commit. It expires (Cloudflare's `__cf_bm` cookie is
short-lived, ~30-60 min); when `view-workbook.js` reports the URL
redirected to `/login`, just re-run `login-and-save.js`.

## Viewing a workbook headlessly with the saved session

```bash
node view-workbook.js <workbookUrlOrId> [outFile.png] [orgSlug]
# e.g.
node view-workbook.js 31gdvbYG6NRrBcu1eMUfwG pura.png papercranestaging
```

For clicking through pages / interacting, copy `view-workbook.js` as a
starting point -- `page.locator('text="Page Name"').last().click()`
targets the native bottom page-tab bar reliably.
