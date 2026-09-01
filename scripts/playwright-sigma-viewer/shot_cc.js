const { chromium } = require('playwright');
const url = 'https://app.sigmacomputing.com/sigma-psa/workbook/4kHExaOUcl9gZPmR56glda';
async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1600, height: 1100 }, storageState: __dirname + '/session-prod.json' });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.setDefaultTimeout(30000);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForTimeout(25000);
  await page.screenshot({ path: 'cc-top.png', fullPage: false });
  console.log('errors:', JSON.stringify(errors));
  await browser.close();
}
main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
