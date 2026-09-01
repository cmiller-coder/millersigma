const { chromium } = require('playwright');
const url = 'https://app.sigmacomputing.com/sigma-psa/workbook/4kHExaOUcl9gZPmR56glda';
async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1600, height: 700 }, storageState: __dirname + '/session-prod.json' });
  const page = await context.newPage();
  page.setDefaultTimeout(30000);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForTimeout(15000);
  const info = await page.evaluate(() => {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let node, hits = [];
    while (node = walker.nextNode()) {
      if (node.textContent.includes('N/A')) {
        let el = node.parentElement;
        for (let i = 0; i < 6 && el; i++) {
          if (el.title || el.getAttribute('aria-label') || el.getAttribute('data-tooltip')) {
            hits.push({title: el.title, aria: el.getAttribute('aria-label'), dt: el.getAttribute('data-tooltip'), tag: el.tagName, cls: el.className});
          }
          el = el.parentElement;
        }
      }
    }
    return hits;
  });
  console.log(JSON.stringify(info, null, 2));
  await browser.close();
}
main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
