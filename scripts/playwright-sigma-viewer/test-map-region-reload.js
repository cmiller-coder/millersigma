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

  // Select West
  const regionControl = page.locator('text="Select values"').first();
  await regionControl.click({ force: true });
  await page.waitForTimeout(1000);
  const westOption = page.locator('text="West"').last();
  await westOption.click({ force: true });
  await page.waitForTimeout(1000);
  await page.keyboard.press('Escape');
  await page.waitForTimeout(3000);

  console.log('URL after selecting West (before reload):', page.url());
  await page.screenshot({ path: 'map-west-before-reload.png', fullPage: false });

  // Now hard-reload the page to see if the plugin gets a filtered payload on fresh mount
  await page.reload({ waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(12000);
  console.log('URL after reload:', page.url());
  await page.screenshot({ path: 'map-west-after-reload.png', fullPage: false });

  await browser.close();
}

main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
