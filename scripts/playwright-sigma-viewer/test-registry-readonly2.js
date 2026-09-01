const { chromium } = require('playwright');

const URL = 'https://staging.sigmacomputing.io/papercranestaging/workbook/S2UuvIJFdoevwzqB8XeE3';

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1600, height: 900 },
    storageState: __dirname + '/session.json',
  });
  const page = await context.newPage();
  page.setDefaultTimeout(20000);

  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(5000);
  await page.locator('text="Approvals"').last().click({ force: true });
  await page.waitForTimeout(4000);

  // Target the actual table row's Reg Shift cell precisely via the row text "SCN-260817"
  const row = page.locator('text=/SCN-260817/').first();
  await row.scrollIntoViewIfNeeded();
  const box = await row.boundingBox();
  console.log('row box:', box);

  // Click roughly where the Reg Shift column is (to the right of Type column)
  await page.mouse.click(box.x + 620, box.y + 5);
  await page.waitForTimeout(1500);
  await page.screenshot({ path: 'registry-cell-click2.png', fullPage: false });

  await page.keyboard.type('999');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: 'registry-cell-typed2.png', fullPage: false });
  await page.keyboard.press('Enter').catch(() => {});
  await page.waitForTimeout(1500);
  await page.screenshot({ path: 'registry-cell-after-enter2.png', fullPage: false });

  await browser.close();
}

main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
