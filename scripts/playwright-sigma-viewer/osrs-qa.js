// Live QA for the Grand Exchange Merchanting Desk (demeng).
// Usage: node osrs-qa.js            (needs a fresh session-prod.json)
const { chromium } = require('playwright');
const URL_WB = 'https://app.sigmacomputing.com/demeng/workbook/Grand-Exchange-Merchanting-Desk-1wEQo1B18rjKsBEt1H5gLf';
const OUT = '/private/tmp/claude-502/rs';

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    viewport: { width: 1680, height: 1050 },
    storageState: __dirname + '/session-prod.json',
  });
  const page = await ctx.newPage();
  const msgs = [];
  page.on('console', m => { if (m.type() === 'error') msgs.push('[console] ' + m.text()); });
  page.on('pageerror', e => msgs.push('[pageerror] ' + e.message));

  await page.goto(URL_WB, { waitUntil: 'domcontentloaded', timeout: 45000 });
  if (page.url().includes('/login')) {
    console.log('SESSION EXPIRED -> run: node login-and-save-prod.js demeng');
    await browser.close(); process.exit(1);
  }
  await page.waitForTimeout(22000);           // charts + 240-row SQL + plugin iframe

  // what colour did the canvas actually end up?
  const bg = await page.evaluate(() => {
    const el = document.querySelector('[class*="canvas" i],[data-testid*="canvas" i]') || document.body;
    return getComputedStyle(el).backgroundColor;
  });
  console.log('canvas background:', bg);

  // did the plugin iframe load and draw slots?
  const frames = page.frames().filter(f => f.url().includes('osrs-ge-offer-grid'));
  console.log('plugin iframes:', frames.length);
  for (const f of frames) {
    try {
      const info = await f.evaluate(() => ({
        slots: document.querySelectorAll('.slot').length,
        sub: (document.getElementById('sub') || {}).textContent,
        footL: (document.getElementById('fl') || {}).textContent,
        footR: (document.getElementById('fr') || {}).textContent,
      }));
      console.log('  plugin state:', JSON.stringify(info));
      console.log('  -> bound to live data?', info.sub && !info.sub.includes('snapshot') ? 'YES' : 'NO (fallback snapshot)');
    } catch (e) { console.log('  plugin eval failed:', e.message); }
  }

  await page.screenshot({ path: `${OUT}/qa-1-market-top.png` });
  for (let i = 1; i <= 4; i++) {
    await page.mouse.wheel(0, 1100);
    await page.waitForTimeout(2500);
    await page.screenshot({ path: `${OUT}/qa-1-market-scroll${i}.png` });
  }

  // page 2
  const tab = page.locator('text=Merch Desk').first();
  if (await tab.count()) {
    await tab.click();
    await page.waitForTimeout(18000);
    await page.screenshot({ path: `${OUT}/qa-2-desk-top.png` });
    for (let i = 1; i <= 3; i++) {
      await page.mouse.wheel(0, 1100);
      await page.waitForTimeout(2500);
      await page.screenshot({ path: `${OUT}/qa-2-desk-scroll${i}.png` });
    }
  } else { console.log('could not find the Merch Desk tab'); }

  console.log('--- errors ---');
  console.log(msgs.length ? msgs.slice(0, 25).join('\n') : '(none)');
  await browser.close();
})().catch(e => { console.log('FATAL', e.message); process.exit(1); });
