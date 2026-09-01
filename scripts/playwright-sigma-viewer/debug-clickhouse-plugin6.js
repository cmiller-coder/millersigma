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
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForTimeout(10000);

  const frames = page.frames();
  const pluginFrame = frames.find((f) => f.url().includes('clickhouse-regional-pulse'));
  if (!pluginFrame) { console.log('no plugin frame'); await browser.close(); return; }

  // Try subscribing to tbl-region-agg (authored id) AND kpi-revenue (authored id)
  // directly by their AUTHORED ids too, in case the resolved "source" mapping itself is the problem.
  const result = await pluginFrame.evaluate(() => {
    return new Promise((resolve) => {
      const SDK = window.SigmaPlugin;
      const cfg = SDK.client.config.get();
      const out = { cfg, attempts: {} };
      const tryId = (label, id) => {
        out.attempts[label] = { id, fired: false };
        SDK.client.elements.subscribeToElementData(id, (d) => {
          out.attempts[label].fired = true;
          out.attempts[label].keys = d ? Object.keys(d) : null;
        });
      };
      tryId('resolvedSource', cfg.source);
      tryId('authoredRegionAgg', 'tbl-region-agg');
      tryId('authoredKpiRevenue', 'kpi-revenue');
      tryId('authoredBigbuys', 'tbl-bigbuys');
      setTimeout(() => resolve(out), 20000);
    });
  });
  console.log(JSON.stringify(result, null, 2));
  await browser.close();
}
main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
