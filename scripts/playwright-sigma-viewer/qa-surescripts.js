// Real authenticated interaction QA for the Surescripts build.
const { chromium } = require('playwright');
const WB = '6G0Yo3O3U7digiU4a6Vomt';
const org = 'papercranestaging';
const url = `https://staging.sigmacomputing.io/${org}/workbook/${WB}`;

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1600, height: 1100 }, storageState: __dirname + '/session.json' });
  const page = await context.newPage();
  page.setDefaultTimeout(20000);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(6000);
  if (page.url().includes('/login')) { console.log('SESSION EXPIRED'); process.exit(1); }
  console.log('loaded', page.url());
  await page.screenshot({ path: 'ss-1-page1.png' });

  // 1. Nav pill -> page 2 (click by coordinate -- getByText resolves to a
  // second, non-visible copy of the label somewhere in the DOM)
  await page.mouse.click(1085, 96);
  await page.waitForTimeout(4000);
  await page.screenshot({ path: 'ss-2-nav-to-page2.png' });
  const bodyText1 = await page.evaluate(() => document.body.innerText);
  console.log('page2 loaded, has "Health System Reconciliation":', bodyText1.includes('Health System Reconciliation'));

  // 2. Click a table row (Harborview Regional Medical, first row)
  await page.mouse.click(208, 929);
  await page.waitForTimeout(2500);
  await page.screenshot({ path: 'ss-3-row-selected.png' });
  const bodyText2 = await page.evaluate(() => document.body.innerText);
  console.log('caption shows selected system:', bodyText2.includes('Harborview Regional Medical'));

  // 3. Type outreach note, click Flag
  const noteBox = page.locator('textarea').first();
  await noteBox.click();
  await noteBox.fill('Called CIO office, scheduling enablement review for next week.');
  await page.getByText('Flag for outreach (this session)', { exact: false }).first().click();
  await page.waitForTimeout(2500);
  await page.screenshot({ path: 'ss-4-flagged.png' });
  const bodyText3 = await page.evaluate(() => document.body.innerText);
  console.log('outreach log shows flag + note:', bodyText3.includes('Flagged Harborview') && bodyText3.includes('Called CIO office'));

  // 4. Back to page 1 -- reload the base workbook URL fresh (default page)
  // rather than fighting Sigma's inner scroll container to reach the nav pill.
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(5000);
  console.log('reloaded, url:', page.url());
  const bodyText0 = await page.evaluate(() => document.body.innerText);
  console.log('landed on Command Center:', bodyText0.includes('Network Command Center'));
  await page.screenshot({ path: 'ss-5-back-to-page1.png' });
  await page.mouse.wheel(0, 2600);
  await page.waitForTimeout(1500);
  await page.screenshot({ path: 'ss-5b-scrolled.png' });
  await page.screenshot({ path: 'ss-6-monetization-tab.png' });
  const bodyText4 = await page.evaluate(() => document.body.innerText);
  console.log('monetization tab shows Illustrative Monthly Opportunity:', bodyText4.includes('Illustrative Monthly Opportunity'));

  await browser.close();
}
main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
