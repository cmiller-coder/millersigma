---
name: sigma-embed-portal
description: Scrape a prospect's website, build a branded Sigma embed portal matching their look and feel, and deploy it publicly via Netlify (static hosting + serverless function). Reusable for any prospect.
argument-hint: "[company name]"
tools: Read, Write, Edit, Bash, Glob, Grep, WebFetch
user-invocable: true
---

# /sigma-embed-portal — Prospect Embed Portal Builder

Build a branded Sigma Computing embed portal that mimics a prospect's website and deploy it publicly so the prospect can access it.

## Architecture

```
Netlify (free tier — single deployment)
{company}-embed-portal.netlify.app/
├── public/
│   ├── index.html  ──fetch(/api/embed-url)──→  netlify/functions/embed-url.js
│   ├── app.js      ←──────{ url }──────────    Signs JWT, returns signed URL
│   ├── styles/
│   ├── images/
│   └── webfonts/
└── netlify/functions/
    └── embed-url.js  (Node.js, same domain — no CORS needed)
```

## Step 0: Check Prerequisites

Before gathering inputs, verify the SE's environment is set up.

### Config file check

Credentials are stored in `~/.sigma-portals/{company-slug}.env` — outside any git repo, never committed. If the company name was provided via `$ARGUMENTS`, derive the slug now (lowercase, spaces → hyphens, strip special chars). Otherwise derive it after asking for the company name in Step 1.

Once you have a slug, check for an existing config:

```bash
test -f ~/.sigma-portals/{company-slug}.env && echo "EXISTS" || echo "NOT_FOUND"
```

**If EXISTS:** Read it silently:

```bash
cat ~/.sigma-portals/{company-slug}.env
```

Parse all values from the file and skip Step 1 input gathering entirely. Tell the user: "Found saved credentials for {Company Name} — skipping to Step 2."

**If NOT_FOUND:** Continue with Step 1 as normal. After all inputs are confirmed, offer to save them (see end of Step 1).

### Netlify CLI check

Run:
```bash
netlify --version 2>/dev/null
```

If the command is not found, install it:
```bash
npm install -g netlify-cli
```

Then check if they are logged in:
```bash
netlify status 2>/dev/null
```

If not logged in, tell the user:
> You need a free Netlify account to host your embed portal. Go to https://app.netlify.com/signup to create one, then we'll log you in.

Then run:
```bash
netlify login
```

This opens a browser window. The user clicks "Authorize". Once complete, `netlify status` should show their email address. Tell the user: "You're logged into Netlify. Ready to build!"

## Step 1: Gather Inputs

Collect the following conversationally — don't dump a form. If the user provided some info upfront (like `$ARGUMENTS` for company name), only ask for what's missing.

### Required Inputs

1. **Company Name** — parse from `$ARGUMENTS` if provided, otherwise ask. Used for folder name, site name, page title.
2. **Webpage URL** — the prospect's page to scrape for branding. This is NOT the Sigma URL — it's the prospect's actual website page you want to mimic. Ask: "What page on their website should we base the portal on?"
3. **Sigma CLIENT_ID** — from Administration > Developer Access > Create New (select "Embedding" type). If they don't have one:
   - Go to Administration > Developer Access > Create New
   - Select "Embedding" type
   - Copy the Client ID and Secret (secret is shown only once!)
4. **Sigma EMBED_SECRET** — shown only once when the credential is created.
5. **Sigma Workbook URL** — the published workbook URL. Format: `https://app.sigmacomputing.com/{org}/workbook/{name}-{id}`
6. **Embed User Email** — the email for the embed user (e.g., `embed-user@prospect.com`)
7. **Team Name** — CRITICAL: This team MUST exist in Sigma AND have access to the target workbook. The embed WILL NOT WORK with an empty team. Ask the user to confirm this is set up.
8. **Account Type** — default to `Pro` unless the user specifies otherwise.

### Layout Option

9. **Layout Style** — Ask: "What layout do you want for the embed portal?"
   - **Full-width** (default) — The Sigma embed takes up the full content area below the header. Simple, clean, maximizes dashboard space.
   - **Sidebar navigation** — A vertical sidebar on the left (matching the prospect's website navigation style) with icon-based nav items (e.g., Home, Data, Forecast, etc.). The Sigma embed fills the remaining space to the right. This mimics app-style interfaces like the one in the Verdigris screenshot — a narrow sidebar with icons/labels and the main content area beside it.

   If the user picks sidebar, also ask:
   - **Sidebar nav items** — What items should appear in the sidebar? Collect a list of labels and optionally icons (default to generic icons like 📊, 📈, 🏠, etc.). These are decorative/static unless the user wants multiple workbook embeds (in which case each nav item can point to a different workbook URL — but keep this simple unless requested).

   Save the layout choice in the env file as `LAYOUT=full-width` or `LAYOUT=sidebar`. If sidebar, also save `SIDEBAR_ITEMS` as a comma-separated list of labels (e.g., `Home,Data,M&V,Forecast,End-Use`).

### Login Page Option

10. **Login Page** — Ask: "Do you want a login page before the dashboard? (yes/no, default: no)"
    - If **yes**: A branded login page (email + password fields, prospect's logo, "Sign In" button) is generated. The login is cosmetic — it accepts any input and redirects to the dashboard. This is purely for demo purposes to show the prospect what a gated experience would look like.
    - If **no** (default): Users land directly on the dashboard. No login gate.

    Save in the env file as `LOGIN_PAGE=true` or `LOGIN_PAGE=false`.

### Confirm Sigma Prerequisites

Before proceeding, confirm with the user:
- [ ] Embed credentials created (Client ID + Secret)
- [ ] Team exists in Sigma (e.g., "Embed Users")
- [ ] Team has been granted access to the target workbook
- [ ] Workbook is published

If any of these aren't done, tell them to complete them in Sigma first. The embed will show "You don't have permission" if the team doesn't have workbook access.

### Save credentials for next time

After all inputs are confirmed, ask: "Save these credentials so you don't have to paste them next time?"

If yes:

```bash
mkdir -p ~/.sigma-portals
cat > ~/.sigma-portals/{company-slug}.env << 'EOF'
CLIENT_ID={CLIENT_ID}
EMBED_SECRET={EMBED_SECRET}
EMBED_URL={workbook_url}
EMBED_EMAIL={embed_email}
EMBED_TEAMS={team_name}
EMBED_ACCOUNT_TYPE={account_type}
SESSION_LENGTH=3600
WEBPAGE_URL={webpage_url}
LAYOUT={layout}
SIDEBAR_ITEMS={sidebar_items_or_empty}
LOGIN_PAGE={true_or_false}
EOF
chmod 600 ~/.sigma-portals/{company-slug}.env
```

Tell the user: "Saved to `~/.sigma-portals/{company-slug}.env`. Next time just run `/sigma-embed-portal {Company Name}` and credentials will load automatically."

> **Security note:** `~/.sigma-portals/` lives outside any git repo and is never committed. Files are set to `chmod 600` (owner read/write only).

## Step 2: Scrape & Build the Portal

### 2a. Scrape the prospect's webpage

First, establish a working directory and derive the company slug:

```bash
mkdir -p /tmp/sigma-portals && cd /tmp/sigma-portals
```

Derive `{company}` from the company name: lowercase, spaces replaced with hyphens, special characters removed. Examples: "EECA" → `eeca`, "My Company" → `my-company`, "Acme Corp." → `acme-corp`. Use this slug consistently as the folder name, Netlify site name, and npm package name throughout.

Then scrape:

```bash
curl -sL "{webpage_url}" -o raw-page.html
```

### 2b. Download assets

Extract and download from the scraped HTML:
- CSS files (look for `<link rel="stylesheet" href="...">`)
- Web fonts (look for `@font-face` declarations in the CSS, and `<link rel="preload" ... as="font">`)
- Logo images (look for `<img>` tags in the header and footer)
- Favicon if available

Save to:
- `{company}/styles/` — CSS files
- `{company}/webfonts/` — font files
- `{company}/images/` — logos and images

### 2c. Determine which scraping path to use

Inspect the scraped HTML for existing embedded content:

**Path 1 — Page has an existing iframe/embed:**
Look for `<iframe>`, `<embed>`, or interactive widget containers in the main content area. If found:
- Keep the full page structure (header, nav, content area, sidebar, footer)
- Replace the existing iframe/embed with the Sigma embed iframe
- Update the page title and description text to reference analytics
- Strip tracking scripts (GTM, Pendo, Hotjar, etc.)
- Fix asset paths to point to local copies
- Add font-face overrides in a `<style>` block after the main CSS link

**Path 2 — Normal content page (more common):**
Extract just the site "shell" and build a new content area:
- Extract: header/nav section, footer section, CSS files, fonts, logos, color scheme
- Discard: the page-specific body content (articles, text, images that aren't branding)

**If layout is `full-width`:**
- Build a new main content area:
  - A heading like "{Company Name} Analytics Dashboard"
  - A brief one-liner description
  - The Sigma embed iframe taking up the full content area (height="900" or more)
- The result should look like a native page on their website

**If layout is `sidebar`:**
- Build an app-style layout with a fixed left sidebar and main content area:
  - **Sidebar** (~60-70px wide, full viewport height below the header):
    - Background color derived from the prospect's site (typically dark or matching their nav)
    - Each nav item is a vertically stacked icon + label, centered in the sidebar
    - Use the `SIDEBAR_ITEMS` list for labels. Assign appropriate icons (use inline SVG or emoji as fallback): common mappings are Home=🏠, Data=📊, M&V=📐, Forecast=📈, End-Use=👥, API=</>, Help=❓, Contact=📞, Settings=⚙️
    - Active/selected item gets a highlighted background or left border accent
    - Items are clickable but static (no page navigation) unless multiple workbooks are configured
    - Style should match the prospect's website aesthetic — use their fonts, colors, and spacing patterns
  - **Main content area** (fills remaining width to the right of sidebar):
    - The Sigma embed iframe fills this area completely (use `calc(100vh - headerHeight)` for height, `calc(100vw - sidebarWidth)` for width)
    - No extra heading or description needed — the sidebar provides the navigation context
  - Use CSS flexbox or grid: `display: flex` with the sidebar as a fixed-width column and main as `flex: 1`
  - The header/nav from the prospect's site sits above both sidebar and content
  - No footer needed in sidebar layout (it would interfere with the full-height design)

### 2d. Clean the HTML

For both paths, apply these cleanups:
- Remove ALL tracking/analytics scripts (Google Tag Manager, Pendo, Hotjar, dataLayer, Facebook pixel, etc.)
- Remove `nonce` attributes
- Remove `<base>` tags
- Remove SEO meta tags (og:, twitter:, dublin core, canonical)
- Remove favicon/manifest/homescreen meta tags
- Fix CSS paths to point to local `styles/` directory
- Fix image paths to point to local `images/` directory
- Fix font paths — add a `<style>` block after the CSS link with `@font-face` declarations pointing to local `webfonts/` files
- Add Sigma embed SDK: `<script src="https://cdn.sigmacomputing.com/embed-sdk/v0.4/embed-api.js"></script>`
- Add `<script src="app.js"></script>` before `</body>`
- Remove all other JS files from the original site

### 2e. Inject the Sigma embed

Place this where the embed should go (either replacing existing content in Path 1, or as the main content in Path 2):

```html
<div id="loadingState" style="text-align:center;padding:60px 40px;color:#666;">
  <p>Loading analytics dashboard...</p>
</div>
<div id="errorState" style="display:none;text-align:center;padding:60px 40px;color:#666;">
  <p id="errorMessage">Unable to load the analytics dashboard.</p>
  <button onclick="loadEmbed()" style="margin-top:12px;padding:8px 20px;background:#333;color:#fff;border:none;border-radius:4px;cursor:pointer;font-family:inherit;">Try Again</button>
</div>
<iframe id="sigmaEmbed"
  title="{Company Name} Analytics Dashboard"
  height="900" width="100%"
  frameborder="0"
  allowfullscreen
  style="display:none;border:none;">
</iframe>
```

### 2f. Create app.js

Write `{company}/app.js`:

```javascript
const iframe = document.getElementById('sigmaEmbed');
const loadingState = document.getElementById('loadingState');
const errorState = document.getElementById('errorState');
const errorMessage = document.getElementById('errorMessage');
let refreshTimer = null;
const API_URL = '/api/embed-url';

async function loadEmbed() {
  loadingState.style.display = '';
  errorState.style.display = 'none';
  iframe.style.display = 'none';
  try {
    const res = await fetch(API_URL);
    if (!res.ok) throw new Error('Server returned ' + res.status);
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    iframe.src = data.url;
    iframe.onload = () => { loadingState.style.display = 'none'; iframe.style.display = 'block'; };
    iframe.onerror = () => { showError('The embed failed to load.'); };
    if (refreshTimer) clearTimeout(refreshTimer);
    refreshTimer = setTimeout(loadEmbed, (data.expiresIn || 3600) * 0.8 * 1000);
  } catch (err) { showError(err.message || 'Unable to load the analytics dashboard.'); }
}

function showError(msg) {
  loadingState.style.display = 'none';
  errorState.style.display = '';
  errorMessage.textContent = msg;
}

// --- Login gate (only if LOGIN_PAGE is enabled) ---
if (sessionStorage.getItem('sigma_authenticated') !== 'true') {
  window.location.href = 'login.html';
} else {
  loadEmbed();
}
```

**Note:** `app.js` uses a relative URL (`/api/embed-url`). This works because the Netlify Function and the static files are served from the same domain — no CORS headers or placeholder URLs needed.

When `LOGIN_PAGE=true`, the `app.js` auth guard redirects unauthenticated users to `login.html`. When `LOGIN_PAGE=false`, remove the auth guard block and just call `loadEmbed()` directly.

### 2g. Create login.html (only if LOGIN_PAGE=true)

If the user opted for a login page, generate `{company}/login.html`. This is a cosmetic login — it accepts any input and sets a `sessionStorage` flag to grant access.

The login page should:
- Use the same CSS, fonts, and branding as the main portal (link to the same stylesheets)
- Show the prospect's logo centered above the form
- Have a clean, centered card layout with:
  - **Email** input field (`type="text"`, placeholder="Email address") — do NOT use `type="email"`
  - **Password** input field (`type="text"` with CSS `-webkit-text-security: disc; text-security: disc;`) — do NOT use `type="password"`. Chrome flags `type="password"` on free hosting domains (netlify.app, etc.) as phishing.
  - A **Sign In** button styled with the prospect's primary brand color
  - Optional: a subtle "Forgot password?" link (non-functional, just for realism)
  - Add `autocomplete="off"` to both inputs
- On form submit: set `sessionStorage.setItem('sigma_authenticated', 'true')` and redirect to `index.html`
- No server call — this is purely client-side for demo purposes
- The page should look professional and native to the prospect's site — not like a generic template

Also add a **Sign Out** mechanism to the main portal:
- Add a small "Sign Out" link or button somewhere visible in the header/nav area of `index.html`
- On click: `sessionStorage.removeItem('sigma_authenticated')` and redirect to `login.html`
- Style it to blend with the existing header design

#### Login page template

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Sign In — {Company Name}</title>
  <!-- Same stylesheets as main portal -->
  <link rel="stylesheet" href="styles/{main-stylesheet}.css">
  <style>
    /* Font-face declarations — same as index.html */
    /* ... copy from the main portal ... */

    body { margin: 0; background: #f5f5f5; font-family: inherit; }
    .login-wrapper {
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
    }
    .login-card {
      background: #fff;
      border-radius: 8px;
      box-shadow: 0 2px 16px rgba(0,0,0,0.10);
      padding: 48px 40px 36px;
      max-width: 400px;
      width: 100%;
    }
    .login-card img.logo {
      display: block;
      margin: 0 auto 32px;
      max-height: 48px;
    }
    .login-card h1 {
      font-size: 1.25rem;
      text-align: center;
      margin: 0 0 24px;
      font-weight: 600;
    }
    .login-card label {
      display: block;
      font-size: 0.85rem;
      margin-bottom: 4px;
      color: #333;
    }
    .login-card .mask-input {
      -webkit-text-security: disc;
      text-security: disc;
    }
    .login-card input[type="text"] {
      width: 100%;
      padding: 10px 12px;
      border: 1px solid #ccc;
      border-radius: 4px;
      font-size: 0.95rem;
      margin-bottom: 16px;
      box-sizing: border-box;
    }
    .login-card input:focus {
      outline: none;
      border-color: {brand-color};
      box-shadow: 0 0 0 2px {brand-color}22;
    }
    .login-card button {
      width: 100%;
      padding: 12px;
      background: {brand-color};
      color: #fff;
      border: none;
      border-radius: 4px;
      font-size: 1rem;
      cursor: pointer;
      font-family: inherit;
      font-weight: 600;
    }
    .login-card button:hover { opacity: 0.9; }
    .login-card .forgot {
      display: block;
      text-align: center;
      margin-top: 16px;
      font-size: 0.8rem;
      color: #888;
      text-decoration: none;
    }
    .login-error {
      display: none;
      background: #fee;
      color: #c33;
      padding: 8px 12px;
      border-radius: 4px;
      font-size: 0.85rem;
      margin-bottom: 16px;
    }
  </style>
</head>
<body>
  <div class="login-wrapper">
    <div class="login-card">
      <img class="logo" src="images/{logo-file}" alt="{Company Name}">
      <h1>Sign in to your account</h1>
      <div class="login-error" id="loginError">Invalid email or password.</div>
      <form id="loginForm">
        <label for="email">Email</label>
        <input type="text" id="email" placeholder="Email address" required autocomplete="off">
        <label for="password">Password</label>
        <input type="text" id="password" class="mask-input" placeholder="Password" required autocomplete="off">
        <button type="submit">Sign In</button>
      </form>
      <a href="#" class="forgot">Forgot password?</a>
    </div>
  </div>
  <script>
    // If already authenticated, go straight to dashboard
    if (sessionStorage.getItem('sigma_authenticated') === 'true') {
      window.location.href = 'index.html';
    }
    document.getElementById('loginForm').addEventListener('submit', function(e) {
      e.preventDefault();
      // Cosmetic login — accept any non-empty input
      const email = document.getElementById('email').value.trim();
      const password = document.getElementById('password').value;
      if (email && password) {
        sessionStorage.setItem('sigma_authenticated', 'true');
        window.location.href = 'index.html';
      } else {
        document.getElementById('loginError').style.display = 'block';
      }
    });
  </script>
</body>
</html>
```

Adapt this template to match the prospect's branding:
- Replace `{brand-color}` with the prospect's primary brand color extracted from their site
- Replace `{logo-file}` with the logo filename downloaded in Step 2b
- Replace `{main-stylesheet}` with the actual CSS filename
- Copy the same `@font-face` declarations from `index.html`
- Adjust fonts, colors, and styling to feel native to the prospect's design language

## Step 3: Set Up Netlify Project

The static files built in Step 2 live in `{company}/`. Now wrap them in a Netlify project structure and create the serverless function that signs JWTs.

### 3a. Create the project structure

The final layout will look like this:

```
{company}-portal/
├── netlify.toml
├── package.json
├── netlify/
│   └── functions/
│       └── embed-url.js
└── public/               ← all Step 2 files go here
    ├── index.html
    ├── app.js
    ├── styles/
    ├── images/
    └── webfonts/
```

Create the folders and move the static files into `public/`:

```bash
cd /tmp/sigma-portals && \
mkdir -p {company}-portal/netlify/functions && \
mkdir -p {company}-portal/public && \
cp -r {company}/* {company}-portal/public/
```

### 3b. Create `netlify.toml`

Write `{company}-portal/netlify.toml`:

```toml
[build]
  publish = "public"
  functions = "netlify/functions"

[build.environment]
  NODE_VERSION = "18"

[[redirects]]
  from = "/api/embed-url"
  to = "/.netlify/functions/embed-url"
  status = 200
```

This tells Netlify:
- Serve everything in `public/` as the website
- Deploy files in `netlify/functions/` as serverless functions
- Map `/api/embed-url` → the function (so `app.js` uses a clean path)

### 3c. Create `package.json`

Write `{company}-portal/package.json`:

```json
{
  "name": "{company}-embed-portal",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "jsonwebtoken": "^9.0.0",
    "uuid": "^9.0.0"
  }
}
```

### 3d. Create the Netlify Function

Write `{company}-portal/netlify/functions/embed-url.js`:

```javascript
const jwt = require('jsonwebtoken');
const { v4: uuidv4 } = require('uuid');

exports.handler = async function (event, context) {
  try {
    const clientId      = process.env.CLIENT_ID;
    const embedSecret   = process.env.EMBED_SECRET;
    const embedUrl      = process.env.EMBED_URL;
    const embedEmail    = process.env.EMBED_EMAIL;
    const embedTeams    = process.env.EMBED_TEAMS;
    const accountType   = process.env.EMBED_ACCOUNT_TYPE || 'Pro';
    const sessionLength = parseInt(process.env.SESSION_LENGTH, 10) || 3600;

    const now   = Math.floor(Date.now() / 1000);
    const teams = embedTeams ? embedTeams.split(',').map(t => t.trim()) : [];

    const payload = {
      sub:          embedEmail,
      iss:          clientId,
      jti:          uuidv4(),
      iat:          now,
      exp:          now + sessionLength,
      account_type: accountType,
      teams,
    };

    const token = jwt.sign(payload, embedSecret, {
      algorithm: 'HS256',
      keyid:     clientId,
    });

    const separator = embedUrl.includes('?') ? '&' : '?';
    const signedUrl = `${embedUrl}${separator}:jwt=${token}&:embed=true&:menu_position=bottom`;

    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: signedUrl, expiresIn: sessionLength }),
    };
  } catch (err) {
    return {
      statusCode: 500,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ error: 'Failed to generate embed URL' }),
    };
  }
};
```

No CORS headers are needed — the function and static files share the same Netlify domain.

### 3e. Create the Netlify site and set environment variables

From inside the `{company}-portal/` directory, create the Netlify site:

```bash
cd /tmp/sigma-portals/{company}-portal && netlify sites:create --name {company}-embed-portal
```

> If the name `{company}-embed-portal` is already taken (it's a global Netlify namespace), try `{company}-sigma-portal` or add your initials as a suffix.

Then set the secrets — these are stored securely in Netlify and never written to any file:

```bash
cd /tmp/sigma-portals/{company}-portal && \
netlify env:set CLIENT_ID "{CLIENT_ID}" && \
netlify env:set EMBED_SECRET "{EMBED_SECRET}" && \
netlify env:set EMBED_URL "{workbook_url}" && \
netlify env:set EMBED_EMAIL "{embed_email}" && \
netlify env:set EMBED_TEAMS "{team_name}" && \
netlify env:set EMBED_ACCOUNT_TYPE "{account_type}" && \
netlify env:set SESSION_LENGTH "3600"
```

You can view and update these later at https://app.netlify.com under **Site Settings > Environment Variables**.

## Step 4: Deploy to Netlify

Install function dependencies and deploy:

```bash
cd /tmp/sigma-portals/{company}-portal && npm install && netlify deploy --prod
```

Netlify will:
1. Bundle the installed `jsonwebtoken` and `uuid` modules from `node_modules/` into the function
2. Upload everything in `public/` as the website
3. Deploy `netlify/functions/embed-url.js` as a serverless function
4. Print the live URL when complete — it will look like `https://{company}-embed-portal.netlify.app`

The deploy is live immediately — no build pipeline to wait for.

## Step 5: Verify & Deliver

The `netlify deploy --prod` command prints the live URL directly. Verify the page loads:

```bash
curl -sL -o /dev/null -w "%{http_code}\n" "https://{company}-embed-portal.netlify.app/"
```

Once it returns `200`, test the JWT endpoint directly:

```bash
curl -s "https://{company}-embed-portal.netlify.app/api/embed-url" | head -c 200
```

This should return JSON like `{"url":"https://app.sigmacomputing.com/...?:jwt=...","expiresIn":3600}`.

Then tell the user:

> Your embed portal is live at: **https://{company}-embed-portal.netlify.app/**
>
> Share this URL with the prospect. The Sigma embed loads via a secure JWT signed server-side — no credentials are exposed in the browser.
>
> If you ever need to update environment variables (for example, if the workbook URL changes), go to https://app.netlify.com, select your site, and go to **Site Settings > Environment Variables** — then run `netlify deploy --prod` to apply the changes.

## Troubleshooting

**"You don't have permission to access this page"**
- The `teams` claim is empty or the team doesn't have access to the workbook in Sigma
- Verify: team exists in Sigma, team has workbook access, team name in `EMBED_TEAMS` env var matches exactly (case-sensitive)

**"Invalid input: expected string, received undefined → at kid"**
- The JWT header is missing the `kid` field
- Check that `CLIENT_ID` is set correctly in Netlify environment variables
- Test the function directly: `curl https://{company}-embed-portal.netlify.app/api/embed-url`

**Embed shows loading forever**
- Check browser console for JavaScript errors
- Test the API endpoint directly: `curl https://{company}-embed-portal.netlify.app/api/embed-url`
- If you get a 404, confirm `netlify.toml` has the redirect rule and that it was included in the deploy
- If you get a 500, check the Netlify function logs at https://app.netlify.com under **Functions > embed-url > Logs**

**Page looks broken / unstyled**
- CSS paths may not be correctly pointing to local files
- Check browser console for 404s on CSS/font files
- Verify the `@font-face` override `<style>` block has correct paths

**Environment variable changes not taking effect**
- After updating env vars in the Netlify dashboard, you must redeploy
- Run `netlify deploy --prod` from the `{company}-portal/` directory, or trigger a redeploy from the Netlify dashboard
