const { chromium } = require('playwright');

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1600, height: 1100 },
    storageState: __dirname + '/session-prod.json',
  });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  const url = 'https://app.sigmacomputing.com/barton/workbook/POC-Test-1-7ooLsQk4SddzIlEr4m3nKT?:nodeId=tc-charts-p1';
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForTimeout(6000);

  // Click the chevron dropdown top-right (next to refresh icon)
  await page.mouse.click(1573, 21);
  await page.waitForTimeout(1000);
  await page.screenshot({ path: __dirname + '/barton-topright-menu.png' });

  await browser.close();
}
main().catch(e => { console.log('FATAL', e.message); process.exit(1); });
