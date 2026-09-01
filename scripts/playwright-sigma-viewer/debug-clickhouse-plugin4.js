const { chromium } = require('playwright');
const url = 'https://app.sigmacomputing.com/sigma-psa/workbook/3YeOteXGVbTW4teHF6gTKV';

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1600, height: 1100 },
    storageState: __dirname + '/session-prod.json',
  });
  const page = await context.newPage();
  page.setDefaultTimeout(20000);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForTimeout(8000);

  const frames = page.frames();
  const pluginFrame = frames.find((f) => f.url().includes('clickhouse-regional-pulse'));
  if (!pluginFrame) { console.log('no plugin frame'); await browser.close(); return; }

  const result = await pluginFrame.evaluate(() => {
    return new Promise((resolve) => {
      const SDK = window.SigmaPlugin;
      const out = {};
      const cfg = SDK.client.config.get();
      out.cfg = cfg;
      let colsFired = 0, dataFired = 0;
      try {
        SDK.client.elements.subscribeToElementColumns(cfg.source, (cols) => {
          colsFired++;
          out.colsFired = colsFired;
          out.columns = cols;
        });
      } catch (e) { out.colsError = e.message; }
      try {
        SDK.client.elements.subscribeToElementData(cfg.source, (d) => {
          dataFired++;
          out.dataFired = dataFired;
          out.dataKeys = d ? Object.keys(d) : null;
        });
      } catch (e) { out.dataError = e.message; }
      setTimeout(() => resolve(out), 15000);
    });
  });
  console.log(JSON.stringify(result, null, 2).slice(0, 4000));
  await browser.close();
}
main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
