// Usage: node view-workbook.js <workbookUrlOrId> [outFile.png] [orgSlug]
// Requires session.json in this directory -- run login-and-save.js first
// (or whenever the session has expired / Cloudflare's __cf_bm cookie died).
const { chromium } = require('playwright');

const arg = process.argv[2];
const out = process.argv[3] || 'workbook_live.png';
const org = process.argv[4] || 'papercranestaging';
if (!arg) {
  console.log('Usage: node view-workbook.js <workbookUrlOrId> [outFile.png] [orgSlug]');
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
  page.setDefaultTimeout(10000);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForTimeout(6000);
  console.log('URL:', page.url());
  console.log('Title:', await page.title());
  if (page.url().includes('/login')) {
    console.log('SESSION EXPIRED -- run: node login-and-save.js');
    await browser.close();
    process.exit(1);
  }
  await page.screenshot({ path: out, fullPage: false });
  console.log('Saved screenshot to', out);
  await browser.close();
}

main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
