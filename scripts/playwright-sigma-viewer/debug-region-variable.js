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

  // Find the plugin's iframe and read window.__lastRegionFilterRaw inside it
  const frames = page.frames();
  console.log('Frame URLs:', frames.map(f => f.url()).filter(u => u.includes('netlify')));

  const pluginFrame = frames.find(f => f.url().includes('sigma-motors-signal-radar'));
  if (!pluginFrame) {
    console.log('NO PLUGIN IFRAME FOUND');
    await browser.close();
    return;
  }

  const before = await pluginFrame.evaluate(() => window.__lastRegionFilterRaw === undefined ? 'UNDEFINED (never called)' : JSON.stringify(window.__lastRegionFilterRaw));
  console.log('Region filter raw BEFORE selecting West:', before);

  // Select West
  const regionControl = page.locator('text="Select values"').first();
  await regionControl.click({ force: true });
  await page.waitForTimeout(1000);
  const westOption = page.locator('text="West"').last();
  await westOption.click({ force: true });
  await page.keyboard.press('Escape');
  await page.waitForTimeout(6000);

  const after = await pluginFrame.evaluate(() => window.__lastRegionFilterRaw === undefined ? 'UNDEFINED (never called)' : JSON.stringify(window.__lastRegionFilterRaw));
  console.log('Region filter raw AFTER selecting West:', after);

  await browser.close();
}

main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
