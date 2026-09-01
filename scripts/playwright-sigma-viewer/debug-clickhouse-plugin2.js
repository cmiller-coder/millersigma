const { chromium } = require('playwright');
const url = 'https://app.sigmacomputing.com/sigma-psa/workbook/3YeOteXGVbTW4teHF6gTKV';

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1600, height: 1100 },
    storageState: __dirname + '/session-prod.json',
  });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForTimeout(8000);

  const frames = page.frames();
  const pluginFrame = frames.find((f) => f.url().includes('clickhouse-regional-pulse'));
  if (!pluginFrame) { console.log('no plugin frame'); await browser.close(); return; }

  const result = await pluginFrame.evaluate(() => {
    return new Promise((resolve) => {
      const SDK = window.SigmaPlugin;
      const cfg = SDK.client.config.get();
      const out = { cfg };
      try {
        const unsub = SDK.client.elements.subscribeToElementData(cfg.source, (d) => {
          out.dataKeys = d ? Object.keys(d) : null;
          out.sample = d ? Object.fromEntries(Object.entries(d).slice(0, 3).map(([k, v]) => [k, Array.isArray(v) ? v.slice(0, 3) : v])) : null;
          resolve(out);
        });
        setTimeout(() => resolve(Object.assign(out, { timedOut: true })), 6000);
      } catch (e) {
        out.error = e.message;
        resolve(out);
      }
    });
  });
  console.log(JSON.stringify(result, null, 2));
  await browser.close();
}
main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
