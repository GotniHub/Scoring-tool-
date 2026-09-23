const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const outputDir = path.join(__dirname, 'assets');
fs.mkdirSync(outputDir, { recursive: true });

async function waitForApp(page) {
  await page.waitForLoadState('domcontentloaded');
  await page.getByText(/Database connected/).waitFor({ timeout: 30000 });
  await page.waitForTimeout(1200);
  await page.addStyleTag({
    content: `
      header[data-testid="stHeader"] { display: none !important; }
      [data-testid="stToolbar"] { display: none !important; }
      footer { display: none !important; }
    `,
  });
}

async function chooseWorkspace(page, label) {
  await page.getByText(label, { exact: true }).first().click();
  await page.waitForTimeout(2200);
}

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  });
  const page = await browser.newPage({ viewport: { width: 1600, height: 950 }, deviceScaleFactor: 1 });
  await page.goto('http://127.0.0.1:8510/Scorecard', { waitUntil: 'domcontentloaded' });
  await waitForApp(page);
  await page.screenshot({ path: path.join(outputDir, 'overview.png') });

  await chooseWorkspace(page, 'Evaluate a brand');
  const assessment = page.locator('[data-testid="stSelectbox"]').first();
  await assessment.click();
  await page.getByText('Adamance', { exact: true }).last().click();
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(outputDir, 'assessment.png') });

  await chooseWorkspace(page, 'Portfolio');
  await page.screenshot({ path: path.join(outputDir, 'portfolio.png') });

  await chooseWorkspace(page, 'Comparative analysis');
  await page.getByRole('tab', { name: 'Brand profile' }).click();
  await page.waitForTimeout(900);
  await page.getByText('Brands in profile', { exact: true }).scrollIntoViewIfNeeded();
  await page.waitForTimeout(500);
  await page.screenshot({ path: path.join(outputDir, 'comparison.png') });

  await chooseWorkspace(page, 'Scoring framework');
  await page.screenshot({ path: path.join(outputDir, 'framework.png') });

  await chooseWorkspace(page, 'Exports');
  await page.getByText('Download Excel review pack', { exact: true }).waitFor({ timeout: 10000 });
  await page.screenshot({ path: path.join(outputDir, 'exports.png') });

  await browser.close();
  console.log(`Saved screenshots to ${outputDir}`);
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
