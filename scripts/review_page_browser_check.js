// Optional headless check of the review page (needs node and the playwright package on NODE_PATH).
//   node scripts/review_page_browser_check.js <review.html> <download-dir> [screenshot.png]
// Presses 1 on the first item, 3 on the second, 2 + a typed value on the third, downloads the decisions and
// prints {"items": [ids], "csv": "<downloaded file text>", "mirror": "<csv built by the page again>"} as JSON.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const [html, dir, shot] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1300, height: 900 }, deviceScaleFactor: 1, acceptDownloads: true });
  const requests = [];
  page.on('request', r => { if (!r.url().startsWith('file:') && !r.url().startsWith('data:') && !r.url().startsWith('blob:')) requests.push(r.url()); });
  await page.goto('file:///' + path.resolve(html).replace(/\\/g, '/'));
  const ids = [];
  const title = async () => (await page.locator('#facts dd').first().textContent());
  ids.push(await title());
  await page.keyboard.press('1');
  ids.push(await title());
  await page.keyboard.press('3');
  ids.push(await title());
  await page.keyboard.press('2');
  await page.locator('#fixrows input').fill('TCV-1401');
  await page.locator('#note').fill('checked against the original');
  await page.keyboard.press('Escape');
  const progress = await page.locator('#progress').textContent();
  if (shot) {
    await page.evaluate(() => window.scrollTo(0, 0));
    fs.mkdirSync(path.dirname(path.resolve(shot)), { recursive: true });
    await page.screenshot({ path: shot });
  }
  const [dl] = await Promise.all([page.waitForEvent('download'), page.click('#dl')]);
  const file = path.join(dir, 'review_decisions.csv');
  await dl.saveAs(file);
  const mirror = await page.evaluate(() => window.__reviewCsv());
  // persistence: reload and read the progress line again
  await page.reload();
  const after = await page.locator('#progress').textContent();
  await browser.close();
  process.stdout.write(JSON.stringify({ items: ids, csv: fs.readFileSync(file, 'utf8'), mirror, progress, after, requests }));
})().catch(e => { console.error(e); process.exit(1); });
