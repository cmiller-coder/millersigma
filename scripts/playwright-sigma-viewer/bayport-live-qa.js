// Live interactive QA pass for the BayPort Credit Union workbook.
const { chromium } = require('playwright');

const WB = '7kD7vLEe3MudXSNYLh7cCx';
const URL = `https://staging.sigmacomputing.io/papercranestaging/workbook/${WB}`;
const OUT = __dirname + '/bayport-qa';

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1600, height: 1100 },
    storageState: __dirname + '/session.json',
  });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);

  const errors = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push('[console] ' + msg.text());
  });
  page.on('pageerror', (err) => errors.push('[pageerror] ' + err.message));

  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(8000);
  console.log('URL:', page.url());
  console.log('Title:', await page.title());
  if (page.url().includes('/login')) {
    console.log('SESSION EXPIRED -- run: node login-and-save.js');
    await browser.close();
    process.exit(1);
  }

  await page.screenshot({ path: OUT + '-1-command-center.png', fullPage: false });
  console.log('saved', OUT + '-1-command-center.png');

  // Scroll down to bring the bespoke plugin into view and give it time to
  // subscribe/render live data (not the headless-export stub).
  await page.mouse.wheel(0, 1400);
  await page.waitForTimeout(4000);
  await page.screenshot({ path: OUT + '-2-branch-plugin.png', fullPage: false });
  console.log('saved', OUT + '-2-branch-plugin.png');

  // Click into the Rate Planning page and exercise the shock control.
  try {
    await page.locator('text="Rate Planning"').last().click();
    await page.waitForTimeout(4000);
    await page.screenshot({ path: OUT + '-3-rate-planning.png', fullPage: false });
    console.log('saved', OUT + '-3-rate-planning.png');

    const shock100 = page.locator('text="+100"').last();
    await shock100.click({ timeout: 8000 });
    await page.waitForTimeout(4000);
    await page.screenshot({ path: OUT + '-4-rate-shock-100.png', fullPage: false });
    console.log('saved', OUT + '-4-rate-shock-100.png (clicked +100bps shock)');
  } catch (e) {
    console.log('Rate Planning interaction issue:', e.message);
  }

  // Click into Member Segments and try a filter.
  try {
    await page.locator('text="Member Segments"').last().click();
    await page.waitForTimeout(4000);
    await page.screenshot({ path: OUT + '-5-member-segments.png', fullPage: false });
    console.log('saved', OUT + '-5-member-segments.png');
  } catch (e) {
    console.log('Member Segments interaction issue:', e.message);
  }

  console.log('--- console/page errors seen ---');
  if (errors.length === 0) console.log('(none)');
  else errors.slice(0, 40).forEach((e) => console.log(e));

  await browser.close();
}

main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
