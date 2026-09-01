const { chromium } = require('playwright');
const url = 'https://app.sigmacomputing.com/sigma-psa/workbook/3YeOteXGVbTW4teHF6gTKV';
async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1600, height: 1100 }, storageState: __dirname + '/session-prod.json' });
  const page = await context.newPage();
  page.setDefaultTimeout(30000);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForTimeout(25000);
  await page.screenshot({ path: 'clickhouse-live4.png', fullPage: false });
  console.log('done');
  await browser.close();
}
main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
