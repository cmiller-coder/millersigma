// Prod/AWS-host variant of view-workbook.js — for orgs on app.sigmacomputing.com.
// Usage: node view-workbook-prod.js <workbookUrlOrId> [outFile.png] [orgSlug]
// Requires session-prod.json in this directory -- run login-and-save-prod.js first.
const { chromium } = require('playwright');

const arg = process.argv[2];
const out = process.argv[3] || 'workbook_live.png';
const org = process.argv[4] || 'sigma-psa';
if (!arg) {
  console.log('Usage: node view-workbook-prod.js <workbookUrlOrId> [outFile.png] [orgSlug]');
  process.exit(1);
}
const url = arg.startsWith('http')
  ? arg
  : `https://app.sigmacomputing.com/${org}/workbook/${arg}`;

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1600, height: 1100 },
    storageState: __dirname + '/session-prod.json',
  });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  const consoleMsgs = [];
  page.on('console', (msg) => consoleMsgs.push(`[${msg.type()}] ${msg.text()}`));
  page.on('pageerror', (err) => consoleMsgs.push(`[pageerror] ${err.message}`));
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForTimeout(8000);
  console.log('URL:', page.url());
  console.log('Title:', await page.title());
  if (page.url().includes('/login')) {
    console.log('SESSION EXPIRED -- run: node login-and-save-prod.js');
    await browser.close();
    process.exit(1);
  }
  await page.screenshot({ path: out, fullPage: false });
  console.log('Saved screenshot to', out);
  console.log('--- console/page errors ---');
  console.log(consoleMsgs.join('\n') || '(none)');
  await browser.close();
}

main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
