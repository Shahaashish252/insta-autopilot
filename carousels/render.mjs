// Screenshot every <section> of carousels/<slug>/slides.html to 01.png, 02.png … at 1080x1350 (uses the studio's Playwright + Edge).
//   node carousels/render.mjs roop-rooh haar-har man-maan
import { createRequire } from 'module';
import path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';
const here = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(path.join(here, '..', 'studio', 'package.json'));
const { chromium } = require('playwright-core');

const browser = await chromium.launch({ channel: 'msedge' });
const page = await browser.newPage({ viewport: { width: 1080, height: 1350 }, deviceScaleFactor: 1 });
for (const slug of process.argv.slice(2)) {
  await page.goto(pathToFileURL(path.join(here, slug, 'slides.html')).href);
  await page.evaluate(() => document.fonts.ready);
  const n = await page.locator('section').count();
  for (let i = 0; i < n; i++) {
    const file = path.join(here, slug, String(i + 1).padStart(2, '0') + '.png');
    await page.locator('section').nth(i).screenshot({ path: file });
  }
  console.log(slug, n, 'slides');
}
await browser.close();
