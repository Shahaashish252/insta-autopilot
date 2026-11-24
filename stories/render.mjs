// Screenshot each <section> of stories/_build/stories.html to queue/<slug>/story.jpg (uses the studio's Playwright + Edge)
import { createRequire } from 'module'; import path from 'path'; import { fileURLToPath, pathToFileURL } from 'url';
const here = path.dirname(fileURLToPath(import.meta.url)), root = path.join(here, '..');
const { chromium } = createRequire(path.join(root, 'studio', 'package.json'))('playwright-core');
const browser = await chromium.launch({ channel: 'msedge' });
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
await page.goto(pathToFileURL(path.join(here, '_build', 'stories.html')).href);
await page.evaluate(() => document.fonts.ready);
const secs = page.locator('section'), n = await secs.count();
for (let i = 0; i < n; i++) {
  const slug = await secs.nth(i).getAttribute('data-slug');
  await secs.nth(i).screenshot({ path: path.join(root, 'queue', slug, 'story.jpg'), type: 'jpeg', quality: 88 });
}
console.log(n, 'story images');
await browser.close();
