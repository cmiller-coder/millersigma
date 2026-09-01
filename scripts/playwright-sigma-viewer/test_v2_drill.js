const { chromium } = require('playwright');
const url = 'https://app.sigmacomputing.com/sigma-psa/workbook/7avlOIOKvWw4c052FV9mm8';
async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1600, height: 1100 }, storageState: __dirname + '/session-prod.json' });
  const page = await context.newPage();
  page.setDefaultTimeout(30000);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForTimeout(20000);
  await page.locator('text="Product Detail"').first().click();
  await page.waitForTimeout(6000);
  const btns = page.locator('text=/View detail/i');
  await btns.first().click({ timeout: 8000 }).catch(e => console.log('click failed', e.message));
  await page.waitForTimeout(4000);
  await page.screenshot({ path: 'v2-drill.png' });
  await browser.close();
}
main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
