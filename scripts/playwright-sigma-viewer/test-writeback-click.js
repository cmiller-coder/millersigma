// Live authenticated click test for insert-rows write-back on staging.
// Opens the ZZ writeback-live-test workbook, clicks "Insert test row",
// waits, reloads, and reports whether the note actually appears in the table.
const { chromium } = require('playwright');

const wbId = process.argv[2] || '1GxCGWI7Tw0caq4XG2FDQf';
const org = 'papercranestaging';
const url = `https://staging.sigmacomputing.io/${org}/workbook/${wbId}`;

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1600, height: 1100 },
    storageState: __dirname + '/session.json',
  });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  page.on('console', msg => console.log('CONSOLE:', msg.type(), msg.text().slice(0, 200)));
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(6000);
  console.log('URL after load:', page.url());
  if (page.url().includes('/login')) {
    console.log('SESSION EXPIRED');
    await browser.close();
    process.exit(1);
  }
  await page.screenshot({ path: 'wb-before-click.png' });

  const btn = page.getByText('Insert test row', { exact: false }).first();
  await btn.waitFor({ state: 'visible', timeout: 15000 });
  console.log('button found, clicking...');
  await btn.click();
  await page.waitForTimeout(4000);
  await page.screenshot({ path: 'wb-after-click.png' });

  // Look for any toast/error text on the page after the click.
  const bodyText = await page.evaluate(() => document.body.innerText);
  const hasDraftError = /draft mode/i.test(bodyText);
  const hasLiveClickText = /live click test/i.test(bodyText);
  console.log('contains "draft mode" error text:', hasDraftError);
  console.log('contains inserted "live click test" text:', hasLiveClickText);

  // Reload fresh and check again (in case the toast is what we saw, not the table).
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(6000);
  await page.screenshot({ path: 'wb-after-reload.png' });
  const bodyText2 = await page.evaluate(() => document.body.innerText);
  console.log('AFTER RELOAD contains "live click test":', /live click test/i.test(bodyText2));
  console.log('AFTER RELOAD contains "draft mode":', /draft mode/i.test(bodyText2));

  await browser.close();
}

main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
