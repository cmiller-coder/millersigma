const { chromium } = require('playwright');
const url = 'https://app.sigmacomputing.com/sigma-psa/workbook/4kHExaOUcl9gZPmR56glda';
async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1600, height: 1100 }, storageState: __dirname + '/session-prod.json' });
  const page = await context.newPage();
  page.setDefaultTimeout(30000);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForTimeout(20000);
  await page.locator('text="Product Detail"').first().click();
  await page.waitForTimeout(8000);
  await page.screenshot({ path: 'final-tab2.png' });
  await browser.close();
}
main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
