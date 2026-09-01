const { chromium } = require('playwright');
const url = 'https://app.sigmacomputing.com/sigma-psa/workbook/3YeOteXGVbTW4teHF6gTKV';
async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1600, height: 1100 }, storageState: __dirname + '/session-prod.json' });
  const page = await context.newPage();
  page.setDefaultTimeout(30000);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForTimeout(15000);

  await page.locator('text="Select values"').first().click();
  await page.waitForTimeout(1500);
  // Click the checkbox in the row that contains the text "West" (exact, within the dropdown list)
  const row = page.locator('div').filter({ hasText: /^West[\d,]*$/ }).last();
  await row.locator('input[type="checkbox"], [role="checkbox"]').first().click({ timeout: 5000 }).catch(async (e) => {
    console.log('checkbox click failed, trying row click:', e.message);
    await row.click({ timeout: 5000 });
  });
  await page.keyboard.press('Escape');
  await page.waitForTimeout(10000);
  await page.screenshot({ path: 'filter-after2.png' });
  console.log('done');
  await browser.close();
}
main().then(() => process.exit(0)).catch((e) => { console.log('FATAL', e.message); process.exit(1); });
