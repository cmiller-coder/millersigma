const { chromium } = require('playwright');
const url = 'https://app.sigmacomputing.com/sigma-psa/workbook/3YeOteXGVbTW4teHF6gTKV';

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1600, height: 1100 },
    storageState: __dirname + '/session-prod.json',
  });
  const page = await context.newPage();
  page.setDefaultTimeout(30000);
  page.on('console', (msg) => console.log(`[main ${msg.type()}]`, msg.text()));
  page.on('pageerror', (err) => console.log('[main error]', err.message));
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForTimeout(10000);

  const frames = page.frames();
  const pluginFrame = frames.find((f) => f.url().includes('clickhouse-regional-pulse'));
  if (!pluginFrame) { console.log('no plugin frame'); await browser.close(); return; }
  pluginFrame.on('console', (msg) => console.log(`[plugin ${msg.type()}]`, msg.text()));

  const result = await pluginFrame.evaluate(() => {
    return new Promise((resolve) => {
      const SDK = window.SigmaPlugin;
      const cfg = SDK.client.config.get();
      const out = { cfg, messages: [] };
      const origPost = window.parent.postMessage.bind(window.parent);
      window.addEventListener('message', (ev) => {
        out.messages.push({ from: ev.origin, data: typeof ev.data === 'string' ? ev.data.slice(0,300) : JSON.stringify(ev.data).slice(0,300) });
      });
      SDK.client.elements.subscribeToElementData(cfg.source, (d) => {
        out.dataFired = true;
        out.dataKeys = d ? Object.keys(d) : null;
      });
      setTimeout(() => resolve(out), 25000);
    });
  });
  console.log(JSON.stringify(result, null, 2).slice(0, 6000));
  await browser.close();
}
main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
