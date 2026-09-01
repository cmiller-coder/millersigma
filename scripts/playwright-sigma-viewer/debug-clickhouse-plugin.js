// Debug why the ClickHouse Regional Pulse plugin isn't getting live data.
// Usage: node debug-clickhouse-plugin.js
const { chromium } = require('playwright');

const url = 'https://app.sigmacomputing.com/sigma-psa/workbook/3YeOteXGVbTW4teHF6gTKV';

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1600, height: 1100 },
    storageState: __dirname + '/session-prod.json',
  });
  const page = await context.newPage();
  page.on('console', (msg) => console.log(`[page ${msg.type()}]`, msg.text()));
  page.on('pageerror', (err) => console.log('[page error]', err.message));
  page.setDefaultTimeout(15000);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForTimeout(8000);

  const frames = page.frames();
  console.log('total frames:', frames.length);
  for (const f of frames) {
    console.log('frame url:', f.url());
  }

  const pluginFrame = frames.find((f) => f.url().includes('clickhouse-regional-pulse'));
  if (!pluginFrame) {
    console.log('!! could not find plugin iframe by URL');
    await browser.close();
    return;
  }
  console.log('found plugin frame:', pluginFrame.url());

  pluginFrame.on('console', (msg) => console.log(`[plugin-frame ${msg.type()}]`, msg.text()));

  const result = await pluginFrame.evaluate(() => {
    const out = {};
    out.hasSigmaPlugin = !!window.SigmaPlugin;
    out.hasSigmaComputing = !!(window.sigmaComputing && window.sigmaComputing.plugin);
    out.hasReact = !!window.React;
    out.hasReactDOM = !!window.ReactDOM;
    try {
      const SDK = window.SigmaPlugin || (window.sigmaComputing && window.sigmaComputing.plugin);
      if (SDK && SDK.client && SDK.client.config && SDK.client.config.getConfig) {
        out.currentConfig = SDK.client.config.getConfig();
      } else if (SDK && SDK.client) {
        out.clientKeys = Object.keys(SDK.client);
        out.configKeys = SDK.client.config ? Object.keys(SDK.client.config) : null;
      }
    } catch (e) {
      out.configError = e.message;
    }
    out.rootHTML = document.getElementById('root') ? document.getElementById('root').innerHTML.slice(0, 500) : null;
    return out;
  });
  console.log('plugin frame inspection:', JSON.stringify(result, null, 2));

  await page.screenshot({ path: 'clickhouse-debug.png', fullPage: false });
  await browser.close();
}

main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
