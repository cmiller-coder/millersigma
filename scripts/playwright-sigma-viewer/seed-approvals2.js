// v2: close any "Custom view" state before interacting, since input-table
// insert-rows errors with "Edits can only be made in draft mode" while a
// custom view (created automatically when you change a control) is active.
const { chromium } = require('playwright');

const workbookId = process.argv[2];
const org = process.argv[3] || 'papercranestaging';
const url = `https://staging.sigmacomputing.io/${org}/workbook/${workbookId}`;

async function closeCustomViewIfPresent(page) {
  const closeBtn = page.locator('text="Close view"');
  if (await closeBtn.count()) {
    await closeBtn.first().click();
    await page.waitForTimeout(2000);
  }
}

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
  // Check for an error toast immediately after submit.
  const err = page.locator('text="Error in Insert row'.replace(/'/g, '"'));
  const errCount = await page.locator('text=/Error in Insert row/').count();
  if (errCount) {
    console.log('  -> insert error still present after shift=' + shiftValue);
  } else {
    console.log('  -> submitted shift=' + shiftValue + ' OK');
  }
  await closeCustomViewIfPresent(page);
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
  await closeCustomViewIfPresent(page);

  for (const shift of [14, 6, 20, 10]) {
    console.log('Submitting scenario (shift=' + shift + ')...');
    await setShiftAndSubmit(page, shift);
  }

  await page.locator('text="Approvals"').last().click();
  await page.waitForTimeout(3000);
  await page.screenshot({ path: __dirname + '/seed-after-submits2.png', fullPage: false });
  console.log('Done, screenshot saved.');

  await browser.close();
}

main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
