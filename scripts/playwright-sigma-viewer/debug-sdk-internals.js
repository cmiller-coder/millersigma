const { chromium } = require('playwright');
const URL = 'https://staging.sigmacomputing.io/papercranestaging/workbook/S2UuvIJFdoevwzqB8XeE3';

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1600, height: 1200 },
    storageState: __dirname + '/session.json',
  });
  const page = await context.newPage();
  page.setDefaultTimeout(20000);
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(8000);

  const frames = page.frames();
  const pluginFrame = frames.find(f => f.url().includes('sigma-motors-signal-radar'));
  if (!pluginFrame) { console.log('NO IFRAME'); await browser.close(); return; }

  const info = await pluginFrame.evaluate(() => {
    var out = {};
    out.hasSigmaPlugin = !!window.SigmaPlugin;
    out.hasClient = !!(window.SigmaPlugin && window.SigmaPlugin.client);
    var c = window.SigmaPlugin && window.SigmaPlugin.client;
    out.hasSubscribeFn = !!(c && c.config && typeof c.config.subscribeToWorkbookVariable === 'function');
    out.getVariableNow = c && c.config && c.config.getVariable ? (function(){ try { return c.config.getVariable('region_filter'); } catch(e){ return 'ERR:'+e.message; } })() : 'no getVariable';
    out.configNow = c && c.config && c.config.get ? c.config.get() : null;
    return out;
  });
  console.log(JSON.stringify(info, null, 2));
  await browser.close();
}
main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
