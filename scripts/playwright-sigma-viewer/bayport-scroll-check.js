const { chromium } = require('playwright');
const URL = 'https://staging.sigmacomputing.io/papercranestaging/workbook/7kD7vLEe3MudXSNYLh7cCx';
async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1600, height: 1100 }, storageState: __dirname + '/session.json' });
  const page = await context.newPage();
  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(7000);
  // move mouse into the main content column, then wheel repeatedly
  await page.mouse.move(600, 600);
  for (let i = 0; i < 6; i++) {
    await page.mouse.wheel(0, 800);
    await page.waitForTimeout(500);
  }
  await page.waitForTimeout(4000);
  await page.screenshot({ path: __dirname + '/bayport-qa-2b-branch-plugin.png', fullPage: false });
  console.log('saved bayport-qa-2b-branch-plugin.png');
  console.log('--- errors ---');
  errors.forEach(e => console.log(e));
  await browser.close();
}
main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
