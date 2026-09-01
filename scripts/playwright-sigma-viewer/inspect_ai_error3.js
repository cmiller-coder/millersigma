const { chromium } = require('playwright');
const url = 'https://app.sigmacomputing.com/sigma-psa/workbook/4kHExaOUcl9gZPmR56glda';
async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1600, height: 700 }, storageState: __dirname + '/session-prod.json' });
  const page = await context.newPage();
  page.setDefaultTimeout(30000);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForTimeout(15000);
  // click the warning triangle icon near "N/A"
  await page.mouse.click(203, 550);
  await page.waitForTimeout(1500);
  await page.screenshot({ path: 'ai-error-click.png' });
  const bodyText = await page.evaluate(() => document.body.innerText);
  const idx = bodyText.indexOf('N/A');
  console.log(bodyText.slice(Math.max(0, idx - 200), idx + 400));
  await browser.close();
}
main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
