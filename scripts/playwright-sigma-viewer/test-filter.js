const { chromium } = require('playwright');
const url = 'https://app.sigmacomputing.com/sigma-psa/workbook/3YeOteXGVbTW4teHF6gTKV';
async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1600, height: 1100 }, storageState: __dirname + '/session-prod.json' });
  const page = await context.newPage();
  page.setDefaultTimeout(30000);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForTimeout(15000);
  await page.screenshot({ path: 'filter-before.png' });

  // Click the Store Region control and select "West" only
  await page.locator('text="Select values"').first().click();
  await page.waitForTimeout(1500);
  await page.screenshot({ path: 'filter-dropdown-open.png' });
  const westOption = page.locator('text="West"').first();
  await westOption.click({ timeout: 5000 }).catch((e) => console.log('click West failed:', e.message));
  await page.keyboard.press('Escape');
  await page.waitForTimeout(8000);
  await page.screenshot({ path: 'filter-after.png' });
  console.log('done');
  await browser.close();
}
main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
