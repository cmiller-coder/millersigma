const { chromium } = require('playwright');
const url = 'https://app.sigmacomputing.com/sigma-psa/workbook/4kHExaOUcl9gZPmR56glda';
async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1600, height: 700 }, storageState: __dirname + '/session-prod.json' });
  const page = await context.newPage();
  page.setDefaultTimeout(30000);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForTimeout(15000);
  const el = await page.locator('text=N/A').first();
  await el.hover();
  await page.waitForTimeout(1500);
  const tooltip = await page.evaluate(() => {
    const els = Array.from(document.querySelectorAll('[role="tooltip"], .tooltip, [class*=tooltip]'));
    return els.map(e => e.textContent).join(' | ');
  });
  console.log('tooltip:', tooltip);
  await page.screenshot({ path: 'ai-error-tooltip.png' });
  await browser.close();
}
main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
