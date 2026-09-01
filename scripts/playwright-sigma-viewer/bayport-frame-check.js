const { chromium } = require('playwright');
const URL = 'https://staging.sigmacomputing.io/papercranestaging/workbook/7kD7vLEe3MudXSNYLh7cCx';
async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1600, height: 1100 }, storageState: __dirname + '/session.json' });
  const page = await context.newPage();
  const errors = [];
  page.on('console', (m) => { errors.push('['+m.type()+'] ' + m.text()); });
  page.on('requestfailed', (r) => errors.push('[requestfailed] ' + r.url() + ' ' + (r.failure()?.errorText||'')));
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(9000);
  await page.mouse.move(600, 600);
  for (let i = 0; i < 6; i++) { await page.mouse.wheel(0, 800); await page.waitForTimeout(500); }
  await page.waitForTimeout(6000);

  const frames = page.frames();
  console.log('frame count:', frames.length);
  for (const f of frames) {
    console.log('FRAME url=', f.url());
  }
  const localFrame = frames.find(f => f.url().includes('localhost:8080'));
  if (localFrame) {
    console.log('found localhost frame, checking content...');
    try {
      const html = await localFrame.evaluate(() => document.body.innerHTML.slice(0, 300));
      console.log('BODY SNIPPET:', html);
      const ttl = await localFrame.evaluate(() => document.getElementById('lcount')?.textContent);
      console.log('lcount textContent:', ttl);
    } catch (e) { console.log('eval failed:', e.message); }
  } else {
    console.log('NO localhost:8080 frame found in DOM');
  }
  await page.screenshot({ path: __dirname + '/bayport-qa-2c-plugin-area.png', fullPage: false });
  console.log('--- console/errors ---');
  errors.slice(0,60).forEach(e => console.log(e));
  await browser.close();
}
main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
