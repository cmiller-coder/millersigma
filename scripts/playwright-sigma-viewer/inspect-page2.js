const { chromium } = require('playwright');

const workbookId = process.argv[2];
const org = process.argv[3] || 'papercranestaging';
const url = `https://staging.sigmacomputing.io/${org}/workbook/${workbookId}`;

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1600, height: 1100 },
    storageState: __dirname + '/session.json',
  });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(4000);
  await page.locator('text="EV & Hybrid Reallocation"').last().click();
  await page.waitForTimeout(4000);

  const frames = page.frames();
  console.log('frame count:', frames.length);
  for (const f of frames) {
    const inputs = await f.locator('input').count();
    const textboxes = await f.locator('[role="textbox"], [role="spinbutton"], [contenteditable="true"]').count();
    if (inputs || textboxes) {
      console.log('frame url:', f.url(), 'inputs:', inputs, 'textbox-like:', textboxes);
    }
  }
  await browser.close();
}

main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
