// Interact with the EV-share shift control on page 2 and confirm the KPIs
// and rollout chart actually recompute live, then screenshot.
const { chromium } = require('playwright');

const workbookId = process.argv[2];
const org = process.argv[3] || 'papercranestaging';
const out = process.argv[4] || 'shift-test.png';
const url = `https://staging.sigmacomputing.io/${org}/workbook/${workbookId}`;

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1600, height: 1100 },
    storageState: __dirname + '/session.json',
  });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(4000);
  if (page.url().includes('/login')) {
    console.log('SESSION EXPIRED -- run: node login-and-save.js');
    await browser.close();
    process.exit(1);
  }
  await page.locator('text="EV & Hybrid Reallocation"').last().click();
  await page.waitForTimeout(3000);

  // Find the EV-share shift number input and set it to 14.
  const input = page.locator('input[type="number"]').first();
  await input.click({ clickCount: 3 });
  await input.fill('14');
  await input.press('Tab');
  await page.waitForTimeout(6000);

  console.log('URL:', page.url());
  await page.screenshot({ path: out, fullPage: false });
  console.log('Saved screenshot to', out);
  await browser.close();
}

main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
