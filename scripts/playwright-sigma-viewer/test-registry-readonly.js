const { chromium } = require('playwright');

const URL = 'https://staging.sigmacomputing.io/papercranestaging/workbook/S2UuvIJFdoevwzqB8XeE3';

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1600, height: 900 },
    storageState: __dirname + '/session.json',
  });
  const page = await context.newPage();
  page.setDefaultTimeout(20000);
  const errors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()); });

  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(5000);
  if (page.url().includes('/login')) { console.log('SESSION EXPIRED'); process.exit(1); }

  await page.locator('text="Approvals"').last().click({ force: true });
  await page.waitForTimeout(4000);
  await page.screenshot({ path: 'registry-before-click.png', fullPage: false });

  // Try clicking directly into the Reg Shift cell (value "0")
  const cell = page.locator('text="0"').first();
  await cell.click({ force: true }).catch((e) => console.log('click error (may be expected):', e.message));
  await page.waitForTimeout(1500);
  await page.screenshot({ path: 'registry-after-click.png', fullPage: false });

  // try typing to see if it's actually editable
  await page.keyboard.type('999').catch(() => {});
  await page.waitForTimeout(1000);
  await page.screenshot({ path: 'registry-after-type.png', fullPage: false });

  console.log('console errors:', errors.slice(0, 10));
  await browser.close();
}

main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
