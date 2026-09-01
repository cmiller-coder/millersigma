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

  // Go to Product Detail tab and click "View detail" on PC Gaming card
  await page.locator('text="Product Detail"').first().click();
  await page.waitForTimeout(6000);
  await page.screenshot({ path: 'drill-2-tab.png' });

  const viewDetailBtns = page.locator('text=/View detail/i');
  const count = await viewDetailBtns.count();
  console.log('View detail button count:', count);
  if (count > 0) {
    await viewDetailBtns.first().click({ timeout: 8000 }).catch(e => console.log('click failed:', e.message));
    await page.waitForTimeout(4000);
    await page.screenshot({ path: 'drill-3-after-card-click.png' });
  }
  console.log('errors:', JSON.stringify(errors));
  await browser.close();
}
main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
