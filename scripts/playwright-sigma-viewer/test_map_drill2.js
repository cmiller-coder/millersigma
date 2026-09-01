const { chromium } = require('playwright');
const url = 'https://app.sigmacomputing.com/sigma-psa/workbook/4kHExaOUcl9gZPmR56glda';
async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1600, height: 1100 }, storageState: __dirname + '/session-prod.json' });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.setDefaultTimeout(15000);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForTimeout(20000);
  await page.screenshot({ path: 'map-before-click.png', clip: { x: 0, y: 780, width: 1170, height: 300 } });

  // click on California (red/pink region, bottom-left of the map)
  await page.mouse.click(60, 1030);
  await page.waitForTimeout(5000);
  await page.screenshot({ path: 'map-after-click.png', clip: { x: 0, y: 630, width: 1600, height: 460 } });
  console.log('errors:', JSON.stringify(errors));
  await browser.close();
}
main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
