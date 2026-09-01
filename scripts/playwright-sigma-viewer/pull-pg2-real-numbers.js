const { chromium } = require('playwright');

const URL = 'https://staging.sigmacomputing.io/papercranestaging/workbook/S2UuvIJFdoevwzqB8XeE3';

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1600, height: 1300 },
    storageState: __dirname + '/session.json',
  });
  const page = await context.newPage();
  page.setDefaultTimeout(20000);
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(6000);
  if (page.url().includes('/login')) {
    console.log('SESSION EXPIRED');
    process.exit(1);
  }
  await page.locator('text="EV & Hybrid Reallocation"').last().click({ force: true });
  await page.waitForTimeout(4000);

  await page.screenshot({ path: 'pg2-baseline-real.png', fullPage: false });
  console.log('--- BASELINE (shift=0) ---');
  console.log(await page.locator('body').innerText());

  const input = page.locator('text="EV-share shift"').locator('xpath=following::input[1]');
  await input.click({ clickCount: 3 });
  await input.fill('15');
  await input.press('Tab');
  await page.waitForTimeout(9000);

  await page.screenshot({ path: 'pg2-shift15-real.png', fullPage: false });
  console.log('--- AFTER SHIFT = 15 ---');
  console.log(await page.locator('body').innerText());

  await browser.close();
}

main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
