// Seed the Approvals registry with real rows by actually driving the product:
// submit a few scenarios with different EV-share shifts on page 2, then go
// approve/reject a couple on page 3. Real interactions, not fake seed data.
const { chromium } = require('playwright');

const workbookId = process.argv[2];
const org = process.argv[3] || 'papercranestaging';
const url = `https://staging.sigmacomputing.io/${org}/workbook/${workbookId}`;

async function setShiftAndSubmit(page, shiftValue) {
  await page.locator('text="EV & Hybrid Reallocation"').last().click();
  await page.waitForTimeout(2500);
  const input = page.locator('input').nth(1);
  await input.click({ clickCount: 3 });
  await input.fill(String(shiftValue));
  await input.press('Enter');
  await page.waitForTimeout(1500);
  await page.locator('text="Save & submit for approval"').last().click();
  await page.waitForTimeout(3000);
}

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

  console.log('Submitting scenario 1 (shift=14)...');
  await setShiftAndSubmit(page, 14);
  console.log('Submitting scenario 2 (shift=6)...');
  await setShiftAndSubmit(page, 6);
  console.log('Submitting scenario 3 (shift=20)...');
  await setShiftAndSubmit(page, 20);
  console.log('Submitting scenario 4 (shift=10)...');
  await setShiftAndSubmit(page, 10);

  await page.locator('text="Approvals"').last().click();
  await page.waitForTimeout(3000);
  await page.screenshot({ path: __dirname + '/seed-after-submits.png', fullPage: false });
  console.log('Submitted 4 scenarios, screenshot saved.');

  await browser.close();
}

main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
