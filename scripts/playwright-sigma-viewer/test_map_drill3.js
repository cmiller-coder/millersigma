const { chromium } = require('playwright');
const url = 'https://app.sigmacomputing.com/sigma-psa/workbook/4kHExaOUcl9gZPmR56glda';
async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1600, height: 1300 }, storageState: __dirname + '/session-prod.json' });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForTimeout(20000);
  await page.screenshot({ path: 'map-full-before.png' });

  // find California precisely via the accessibility tree / SVG title if possible
  const region = await page.locator('path[aria-label*="California" i], [data-region*="CA" i], text=/California/i').first();
  const exists = await region.count();
  console.log('California locator count:', exists);
  if (exists) {
    await region.click({ timeout: 8000 }).catch(e => console.log('region click failed', e.message));
  } else {
    await page.mouse.click(60, 990);
  }
  await page.waitForTimeout(5000);
  await page.screenshot({ path: 'map-full-after.png' });
  await browser.close();
}
main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
