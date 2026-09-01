const { chromium } = require('playwright');
const URL = 'https://staging.sigmacomputing.io/papercranestaging/workbook/7kD7vLEe3MudXSNYLh7cCx';
async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1600, height: 300 }, storageState: __dirname + '/session.json' });
  const page = await context.newPage();
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(7000);
  await page.screenshot({ path: __dirname + '/bayport-stmt-1.png' });

  await page.locator('text="Rate Planning"').last().click();
  await page.waitForTimeout(3500);
  await page.screenshot({ path: __dirname + '/bayport-stmt-2.png' });

  await page.locator('text="Member Segments"').last().click();
  await page.waitForTimeout(3500);
  await page.screenshot({ path: __dirname + '/bayport-stmt-3.png' });
  console.log('done');
  await browser.close();
}
main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
