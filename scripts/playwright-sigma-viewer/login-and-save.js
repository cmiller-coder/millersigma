const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const page = await context.newPage();
  await page.goto('https://staging.sigmacomputing.io/papercranestaging/login');

  console.log('\n>>> A browser window just opened. Log in to papercranestaging there (SSO/MFA is fine).');
  console.log('>>> Waiting for you to land back on staging.sigmacomputing.io, logged in (up to 5 minutes)...\n');

  const deadline = Date.now() + 300000;
  let landed = false;
  while (Date.now() < deadline) {
    const u = new URL(page.url());
    if (u.hostname === 'staging.sigmacomputing.io' && !u.pathname.includes('/login')) {
      landed = true;
      break;
    }
    await page.waitForTimeout(2000);
  }

  if (!landed) {
    console.log('Timed out waiting for login to land back on staging.sigmacomputing.io.');
    console.log('Current URL:', page.url());
    await browser.close();
    process.exit(1);
  }

  // give the SPA a moment to actually persist its auth token/cookie after landing
  await page.waitForTimeout(4000);
  await context.storageState({ path: __dirname + '/session.json' });
  console.log('Landed on:', page.url());
  console.log('Session saved to session.json. You can close the browser window now.');
  await browser.close();
})();
