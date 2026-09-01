const { chromium } = require('playwright');
const url = 'https://app.sigmacomputing.com/sigma-psa/workbook/4kHExaOUcl9gZPmR56glda';
async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1600, height: 1100 }, storageState: __dirname + '/session-prod.json' });
  const page = await context.newPage();
  page.setDefaultTimeout(30000);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForTimeout(20000);
  // scroll specifically over the map/tabbed-container area
  await page.mouse.move(400, 900);
  await page.mouse.wheel(0, 1500);
  await page.waitForTimeout(3000);
  await page.screenshot({ path: 'cc-scroll3.png' });
  await page.mouse.wheel(0, 1500);
  await page.waitForTimeout(3000);
  await page.screenshot({ path: 'cc-scroll4.png' });
  console.log('done');
  await browser.close();
}
main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
