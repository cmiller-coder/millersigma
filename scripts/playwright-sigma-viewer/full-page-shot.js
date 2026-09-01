const { chromium } = require('playwright');
const url = 'https://app.sigmacomputing.com/sigma-psa/workbook/3YeOteXGVbTW4teHF6gTKV';
async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1600, height: 1100 }, storageState: __dirname + '/session-prod.json' });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.setDefaultTimeout(30000);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForTimeout(20000);
  await page.screenshot({ path: 'clickhouse-final-top.png', fullPage: false });
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(4000);
  await page.screenshot({ path: 'clickhouse-final-bottom.png', fullPage: false });
  console.log('errors:', JSON.stringify(errors));
  await browser.close();
}
main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
