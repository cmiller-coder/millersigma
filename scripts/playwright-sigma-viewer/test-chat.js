const { chromium } = require('playwright');

const workbookId = process.argv[2];
const org = process.argv[3] || 'papercranestaging';
const question = process.argv[4] || 'Which region is most urgent and why?';
const url = `https://staging.sigmacomputing.io/${org}/workbook/${workbookId}`;

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1600, height: 1100 },
    storageState: __dirname + '/session.json',
  });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(5000);
  if (page.url().includes('/login')) {
    console.log('SESSION EXPIRED -- run: node login-and-save.js');
    await browser.close();
    process.exit(1);
  }
  const input = page.locator('[placeholder="Ask anything"], textarea, input[type="text"]').last();
  await input.click();
  await input.fill(question);
  await input.press('Enter');
  console.log('Asked:', question);
  await page.waitForTimeout(12000);
  await page.screenshot({ path: __dirname + '/chat-test-result.png', fullPage: false });
  console.log('Screenshot saved.');
  await browser.close();
}

main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
