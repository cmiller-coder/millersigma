const { chromium } = require('playwright');
const url = 'https://app.sigmacomputing.com/sigma-psa/workbook/4kHExaOUcl9gZPmR56glda';
async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1600, height: 1300 }, storageState: __dirname + '/session-prod.json' });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForTimeout(20000);
  // Click well inside Texas (large, unambiguous state)
  await page.mouse.click(190, 1065);
  await page.waitForTimeout(6000);
  await page.screenshot({ path: 'map-tx-click.png' });
  // also grab just the State control area to read its value clearly
  await page.screenshot({ path: 'map-tx-state-ctrl.png', clip: {x:0, y:1200, width:560, height:100} });
  await browser.close();
}
main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
