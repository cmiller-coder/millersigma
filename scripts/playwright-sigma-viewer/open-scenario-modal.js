// Navigate to page 2, click "+ New scenario" to open the Scenario Studio
// modal, and screenshot the live result -- static export can't render
// overlay/modal content, only a real interactive click can.
const { chromium } = require('playwright');

const workbookId = process.argv[2];
const org = process.argv[3] || 'papercranestaging';
const out = process.argv[4] || 'scenario-modal.png';
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
  await page.locator('text="+ New scenario"').last().click();
  await page.waitForTimeout(3000);

  console.log('URL:', page.url());
  await page.screenshot({ path: out, fullPage: false });
  console.log('Saved screenshot to', out);
  await browser.close();
}

main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
