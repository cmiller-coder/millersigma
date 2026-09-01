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
  const errors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()); });

  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(6000);
  if (page.url().includes('/login')) {
    console.log('SESSION EXPIRED -- run: node login-and-save.js');
    await browser.close();
    process.exit(1);
  }

  await page.screenshot({ path: 'kpi-region-baseline.png', fullPage: false });
  console.log('--- BASELINE (no region filter) ---');
  const kpiTexts1 = await page.locator('text=/EV WAITLIST|HYBRID WAITLIST|LONGEST BACKLOG|MARGIN AT RISK|REGIONS AT RISK/').allTextContents();
  console.log(kpiTexts1);

  // Open the Region "Select values" dropdown
  const regionControl = page.locator('text="Select values"').first();
  await regionControl.click({ force: true });
  await page.waitForTimeout(1000);
  await page.screenshot({ path: 'kpi-region-dropdown-open.png', fullPage: false });

  // Pick "West" option in the opened dropdown/list
  const westOption = page.locator('text="West"').last();
  await westOption.click({ force: true });
  await page.waitForTimeout(1000);
  // close dropdown by pressing Escape or clicking elsewhere
  await page.keyboard.press('Escape');
  await page.waitForTimeout(8000);

  await page.screenshot({ path: 'kpi-region-west.png', fullPage: false });
  console.log('--- AFTER REGION = WEST ---');
  const kpiTexts2 = await page.locator('text=/EV WAITLIST|HYBRID WAITLIST|LONGEST BACKLOG|MARGIN AT RISK|REGIONS AT RISK/').allTextContents();
  console.log(kpiTexts2);

  console.log('CONSOLE ERRORS:', errors.slice(0, 20));

  await browser.close();
}

main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
