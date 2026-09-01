// Same as view-workbook.js but waits longer for Cortex CallText answers to
// resolve before screenshotting, and can click a page tab first.
const { chromium } = require('playwright');

const arg = process.argv[2];
const out = process.argv[3] || 'workbook_live.png';
const org = process.argv[4] || 'papercranestaging';
const tabName = process.argv[5] || null;
if (!arg) {
  console.log('Usage: node view-workbook-longwait.js <workbookUrlOrId> [outFile.png] [orgSlug] [tabName]');
  process.exit(1);
}
const url = arg.startsWith('http')
  ? arg
  : `https://staging.sigmacomputing.io/${org}/workbook/${arg}`;

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
  if (page.url().includes('/login')) {
    console.log('SESSION EXPIRED -- run: node login-and-save.js');
    await browser.close();
    process.exit(1);
  }
  if (tabName) {
    await page.locator('text="' + tabName + '"').last().click();
    await page.waitForTimeout(2000);
  }
  await page.waitForTimeout(14000);
  console.log('URL:', page.url());
  console.log('Title:', await page.title());
  await page.screenshot({ path: out, fullPage: false });
  console.log('Saved screenshot to', out);
  await browser.close();
}

main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
