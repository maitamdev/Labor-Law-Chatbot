// Exercise the real Streamlit navigation without signing in or writing user data.
// NODE_PATH=storage/test_tools/node_modules node scripts/check_navigation.cjs
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const url = process.env.NAVIGATION_URL || 'http://127.0.0.1:8501';
const output = process.env.NAVIGATION_OUTPUT || 'storage/navigation_20261029/browser';

(async () => {
  fs.mkdirSync(output, {recursive:true});
  const cache = path.join(process.env.LOCALAPPDATA, 'ms-playwright');
  const candidates = fs.readdirSync(cache).filter(n => /^chromium-\d+$/.test(n))
    .sort((a, b) => Number(b.split('-')[1]) - Number(a.split('-')[1]));
  const executablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE
    || path.join(cache, candidates[0], 'chrome-win64/chrome.exe');
  const browser = await chromium.launch({headless:true, executablePath});
  const page = await browser.newPage({viewport:{width:1440, height:1000}});
  const errors = [];
  const checks = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => {
    if (message.type() === 'error') errors.push(message.text());
  });

  // Sample across painted frames, including the response to the component event.
  const stableView = async expected => {
    const result = await page.locator('.vl-mount').evaluate((mount, view) =>
      new Promise(resolve => {
        const start = performance.now();
        const seen = [];
        const tick = () => {
          const current = mount.querySelector('.vl-app')?.dataset.view;
          if (current && seen.at(-1) !== current) seen.push(current);
          const elapsed = performance.now() - start;
          if (elapsed < 1200 || (mount.dataset.pendingNavigationId && elapsed < 15000)) requestAnimationFrame(tick);
          else resolve({
            seen,
            finalView:current,
            active:[...mount.querySelectorAll('.nav-item.active')].map(el => el.dataset.view),
            visible:!!mount.querySelector('.view-pane[data-pane="' + view + '"]')?.getClientRects().length,
            acknowledged:!mount.dataset.pendingNavigationId,
          });
        };
        tick();
      }), expected);
    assert.equal(result.finalView, expected, JSON.stringify(result));
    assert.deepEqual(result.seen, [expected], 'Navigation reverted: ' + JSON.stringify(result));
    assert.equal(result.visible, true, 'The selected content is hidden');
    assert.equal(result.acknowledged, true, 'The server has not acknowledged the selected view');
    if (!['chat', 'about'].includes(expected)) assert.deepEqual(result.active, [expected]);
  };

  try {
    await page.goto(url, {waitUntil:'networkidle'});
    await page.locator('.vl-app .header-brand').waitFor({state:'visible', timeout:30000});
    if (process.env.NAVIGATION_QUERY) {
      await page.locator('.view-pane[data-pane="home"] textarea').fill(process.env.NAVIGATION_QUERY);
      await page.locator('.view-pane[data-pane="home"] button[type="submit"]').click();
      await page.locator('.vl-app[data-busy="true"]').waitFor({state:'attached', timeout:30000});
    }
    for (const view of ['documents', 'topics', 'templates', 'situations', 'faq', 'news', 'graph', 'home']) {
      await page.locator('.nav-item[data-view="' + view + '"]').click();
      await stableView(view);
      checks.push('desktop: ' + view);
    }
    for (let i = 0; i < 3; i++) {
      await page.locator('.vl-app').evaluate(app => {
        for (const view of ['documents', 'faq', 'topics', 'news', 'templates', 'graph']) {
          app.querySelector('.nav-item[data-view="' + view + '"]').click();
        }
      });
      await stableView('graph');
      checks.push('rapid navigation: ' + (i + 1));
    }
    for (const delay of [25, 100, 250]) {
      await page.locator('.vl-mount').evaluate(async (mount, delay) => {
        for (const view of ['documents', 'faq', 'topics', 'news', 'templates', 'graph']) {
          mount.querySelector('.nav-item[data-view="' + view + '"]').click();
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }, delay);
      await stableView('graph');
      checks.push('navigation across server updates: ' + delay + 'ms');
    }
    await page.locator('.site-header nav [data-view="about"]').click();
    await stableView('about');
    await page.locator('.header-brand').click();
    await stableView('home');
    checks.push('header navigation');
    await page.screenshot({path:path.join(output, 'desktop.png')});

    await page.setViewportSize({width:390, height:844});
    for (const view of ['faq', 'documents', 'templates', 'situations', 'news', 'graph', 'topics', 'home']) {
      const link = page.locator('.nav-item[data-view="' + view + '"]');
      if (!await link.isVisible()) await page.locator('[data-mobile-menu]').click();
      await link.click();
      await stableView(view);
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      checks.push('mobile: ' + view);
    }
    await page.screenshot({path:path.join(output, 'mobile.png')});
    if (process.env.NAVIGATION_QUERY) {
      await page.locator('.vl-app[data-busy="false"]').waitFor({state:'attached', timeout:240000});
      await stableView('home');
      assert(await page.locator('.assistant-message .answer-markdown').count());
      checks.push('selected view survives background AI completion');
    }
    assert.equal(await page.locator('[data-testid="stException"]').count(), 0);
    assert.deepEqual(errors, []);
    fs.writeFileSync(path.join(output, 'verification.json'), JSON.stringify({url, checks, errors}, null, 2));
    console.log(checks.length + ' navigation checks passed; no stale view across rendered frames.');
  } catch (error) {
    await page.screenshot({path:path.join(output, 'failure.png')}).catch(() => {});
    fs.writeFileSync(path.join(output, 'failure.json'), JSON.stringify({url, checks, errors, failure:String(error)}, null, 2));
    throw error;
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
