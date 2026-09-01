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

  await page.screenshot({ path: 'statement-button-header.png', fullPage: false });

  const [newPage] = await Promise.all([
    context.waitForEvent('page', { timeout: 15000 }).catch(() => null),
    page.locator('text=/Reservation Statement/').first().click({ force: true }),
  ]);

  await page.waitForTimeout(3000);
  if (newPage) {
    await newPage.waitForLoadState('domcontentloaded').catch(() => {});
    await newPage.waitForTimeout(4000);
    console.log('New tab URL:', newPage.url());
    await newPage.screenshot({ path: 'statement-opened.png', fullPage: false });
  } else {
    console.log('No new tab/page opened -- checking current page URL:', page.url());
    await page.screenshot({ path: 'statement-opened-sametab.png', fullPage: false });
  }

  await browser.close();
}

main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
