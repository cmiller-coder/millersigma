const { chromium } = require('playwright');
const url = 'https://app.sigmacomputing.com/sigma-psa/workbook/4kHExaOUcl9gZPmR56glda';
async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1600, height: 1100 }, storageState: __dirname + '/session-prod.json' });
  const page = await context.newPage();
  page.setDefaultTimeout(30000);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForTimeout(20000);
  await page.locator('label:has-text("Product Family") ~ * >> text="Select values"').first().click().catch(async () => {
    await page.locator('text="Select values"').nth(1).click();
  });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: 'cc-filter-dropdown.png' });
  const row = page.locator('div').filter({ hasText: /^PC Gaming[\d,$]*$/ }).last();
  await row.click({ timeout: 5000 }).catch((e) => console.log('row click failed:', e.message));
  await page.keyboard.press('Escape');
  await page.waitForTimeout(8000);
  await page.screenshot({ path: 'cc-filter-after.png' });
  console.log('done');
  await browser.close();
}
main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
