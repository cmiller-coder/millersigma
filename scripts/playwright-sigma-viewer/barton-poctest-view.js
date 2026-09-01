const { chromium } = require('playwright');

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1600, height: 1100 },
    storageState: __dirname + '/session-prod.json',
  });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  const url = 'https://app.sigmacomputing.com/barton/workbook/1O50wP0lbQLaUMMQdInJfN';
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForTimeout(7000);
  console.log('URL:', page.url());
  console.log('Title:', await page.title());
  await page.screenshot({ path: __dirname + '/barton-poctest-live.png' });
  await browser.close();
}
main().catch(e => { console.log('FATAL', e.message); process.exit(1); });
