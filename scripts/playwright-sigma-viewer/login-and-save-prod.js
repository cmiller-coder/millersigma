// Prod/AWS-host variant of login-and-save.js — for orgs on app.sigmacomputing.com
// (e.g. sigma-psa), not the staging.sigmacomputing.io fork the original targets.
// Usage: node login-and-save-prod.js [orgSlug]   (default org: sigma-psa)
const { chromium } = require('playwright');

const org = process.argv[2] || 'sigma-psa';

(async () => {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const page = await context.newPage();
  await page.goto(`https://app.sigmacomputing.com/${org}/login`);

  console.log(`\n>>> A browser window just opened. Log in to ${org} there (SSO/MFA is fine).`);
  console.log('>>> Waiting for you to land back on app.sigmacomputing.com, logged in (up to 5 minutes)...\n');

  const deadline = Date.now() + 300000;
  let landed = false;
  while (Date.now() < deadline) {
    const u = new URL(page.url());
    if (u.hostname === 'app.sigmacomputing.com' && !u.pathname.includes('/login')) {
      landed = true;
      break;
    }
    await page.waitForTimeout(2000);
  }

  if (!landed) {
    console.log('Timed out waiting for login to land back on app.sigmacomputing.com.');
    console.log('Current URL:', page.url());
    await browser.close();
    process.exit(1);
  }

  await page.waitForTimeout(4000);
  await context.storageState({ path: __dirname + '/session-prod.json' });
  console.log('Landed on:', page.url());
  console.log('Session saved to session-prod.json. You can close the browser window now.');
  await browser.close();
})();
