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
  await page.waitForTimeout(5000);

  const closeView = page.locator('text="Close view"');
  if (await closeView.count()) {
    await closeView.click({ force: true });
    await page.waitForTimeout(2000);
    console.log('Closed custom view');
  } else {
    console.log('No custom view banner found -- already clean');
  }
  await page.screenshot({ path: 'reset-confirm.png', fullPage: false });
  await browser.close();
}

main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
