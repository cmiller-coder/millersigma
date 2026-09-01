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

  // The header logo is the top-left image inside the navy header band.
  const img = page.locator('img').first();
  const count = await page.locator('img').count();
  console.log('image count on page:', count);
  const srcs = await page.locator('img').evaluateAll(imgs => imgs.map(i => ({src: i.src, w: i.naturalWidth, h: i.naturalHeight, top: i.getBoundingClientRect().top, left: i.getBoundingClientRect().left})));
  console.log(JSON.stringify(srcs, null, 2));

  await browser.close();
}

main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
