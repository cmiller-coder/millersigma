const { chromium } = require('playwright');

const URL = 'https://staging.sigmacomputing.io/papercranestaging/workbook/S2UuvIJFdoevwzqB8XeE3';

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1600, height: 1200 },
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

  await page.screenshot({ path: 'map-react-baseline.png', fullPage: false });

  // set Value adjust % to 30 (a big jump so any reactivity is obvious)
  const adjustInput = page.locator('input[type="text"], input[type="number"]').filter({ hasText: '' });
  const adjustBox = page.locator('text="Value adjust %"').locator('xpath=following::input[1]');
  await adjustBox.click({ force: true });
  await adjustBox.fill('30');
  await page.keyboard.press('Tab');
  await page.waitForTimeout(9000);

  await page.screenshot({ path: 'map-react-adjust30.png', fullPage: false });
  console.log('done');
  await browser.close();
}

main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
