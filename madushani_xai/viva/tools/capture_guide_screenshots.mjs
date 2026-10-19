// Captures ANNOTATED screenshots for SIMPLE_PRESENTATION_GUIDE.md into
// viva/screenshots/guide/. A red box + label is drawn on the element to click
// or look at. The overlay exists only inside the headless browser; no app code
// is changed. The system must be running (python start-all.py). Node 22+.
//
//   node viva/tools/capture_guide_screenshots.mjs        (from madushani_xai/)
import { spawn } from 'node:child_process'
import { mkdirSync, writeFileSync, mkdtempSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { tmpdir } from 'node:os'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const OUT = join(HERE, '..', 'screenshots', 'guide')
const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
const PORT = 9345
const W = 1280, H = 800, SCALE = 1.25
const sleep = ms => new Promise(r => setTimeout(r, ms))
mkdirSync(OUT, { recursive: true })

// Injected into the page: draws red boxes with labels around elements.
const MARKER = `
window.__clearMarks = () => document.querySelectorAll('.__mark').forEach(e => e.remove());
window.__mark = (el, label, side = 'top') => {
  if (!el) throw new Error('element not found for: ' + label);
  const r = el.getBoundingClientRect(), pad = 6;
  const box = document.createElement('div');
  box.className = '__mark';
  Object.assign(box.style, { position: 'fixed', left: (r.left - pad) + 'px', top: (r.top - pad) + 'px',
    width: (r.width + 2 * pad) + 'px', height: (r.height + 2 * pad) + 'px', border: '4px solid #e00000',
    borderRadius: '8px', boxShadow: '0 0 0 3px rgba(255,255,255,0.85)', zIndex: 2147483646, pointerEvents: 'none' });
  const tag = document.createElement('div');
  tag.className = '__mark';
  tag.textContent = label;
  Object.assign(tag.style, { position: 'fixed', zIndex: 2147483647, background: '#e00000', color: '#fff',
    font: '700 17px Segoe UI, Arial, sans-serif', padding: '6px 12px', borderRadius: '6px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.4)', whiteSpace: 'nowrap', pointerEvents: 'none' });
  document.body.append(box, tag);
  const t = tag.getBoundingClientRect();
  let x = r.left, y = r.top - t.height - 14;
  if (side === 'left') { x = r.left - t.width - 18; y = r.top + r.height / 2 - t.height / 2; }
  if (side === 'right') { x = r.right + 18; y = r.top + r.height / 2 - t.height / 2; }
  if (side === 'bottom') { y = r.bottom + 14; }
  x = Math.max(6, Math.min(x, innerWidth - t.width - 6)); y = Math.max(6, Math.min(y, innerHeight - t.height - 6));
  Object.assign(tag.style, { left: x + 'px', top: y + 'px' });
};
document.querySelectorAll('img[loading="lazy"]').forEach(i => { i.loading = 'eager' });
window.__byText = (sel, text) => [...document.querySelectorAll(sel)].find(e => e.textContent.trim().includes(text));
`

const edge = spawn(EDGE, ['--headless=new', '--disable-gpu', '--no-first-run', '--hide-scrollbars',
  `--user-data-dir=${mkdtempSync(join(tmpdir(), 'viva-guide-'))}`, `--remote-debugging-port=${PORT}`, 'about:blank'],
  { stdio: 'ignore' })

let failures = 0
try {
  let wsUrl
  for (let i = 0; i < 40 && !wsUrl; i++) {
    try { wsUrl = (await (await fetch(`http://127.0.0.1:${PORT}/json`)).json()).find(t => t.type === 'page')?.webSocketDebuggerUrl }
    catch { await sleep(300) }
  }
  const ws = new WebSocket(wsUrl)
  await new Promise(r => ws.addEventListener('open', r, { once: true }))
  let id = 0
  const pending = new Map()
  ws.addEventListener('message', e => {
    const m = JSON.parse(e.data)
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) }
  })
  const send = (method, params = {}) => new Promise(r => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })) })
  const evaluate = async expr => {
    const res = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true })
    if (res.result?.exceptionDetails) throw new Error(res.result.exceptionDetails.exception?.description || 'script error')
    return res.result?.result?.value
  }
  const waitFor = async (expr, ms = 25000) => {
    for (const t0 = Date.now(); Date.now() - t0 < ms;) { if (await evaluate(expr)) return true; await sleep(300) }
    throw new Error('timed out waiting for: ' + expr)
  }
  const visibleImagesLoaded = `[...document.images].filter(i => { const r = i.getBoundingClientRect(); return r.bottom > 0 && r.top < innerHeight })
                                 .every(i => i.complete && i.naturalWidth > 0)`

  await send('Page.enable')
  await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: SCALE, mobile: false })

  // Load a page, run `steps` (in-page JS that scrolls / clicks / marks), save a PNG.
  async function shot(name, url, ready, steps) {
    try {
      await send('Page.navigate', { url })
      await waitFor(`document.readyState === 'complete'`)
      await evaluate(MARKER)
      await waitFor(ready)
      await sleep(900)   // chart entry animations
      await evaluate(`(async () => { ${steps} })()`)
      await sleep(700)
      await waitFor(visibleImagesLoaded)
      const res = await send('Page.captureScreenshot', { format: 'png' })
      writeFileSync(join(OUT, name), Buffer.from(res.result.data, 'base64'))
      console.log('OK   ' + name)
    } catch (e) {
      failures++
      console.log('FAIL ' + name + ': ' + e.message)
    }
  }
  const has = t => `document.body && document.body.innerText.toLowerCase().includes(${JSON.stringify(t.toLowerCase())})`
  const pause = ms => `await new Promise(r => setTimeout(r, ${ms}));`
  const XAI = 'http://localhost:5173'

  // 1. BI dashboard: the 2025-01-25 row and its LIME button
  await shot('g01_bi_click_lime.png', 'http://localhost:3000', has('Recent abnormal days'), `
    const row = [...document.querySelectorAll('tr')].find(r => r.textContent.includes('2025-01-25'));
    row.scrollIntoView({ block: 'center' }); ${pause(400)}
    __mark(row.querySelector('td'), '1. Find 2025-01-25', 'left');
    __mark([...row.querySelectorAll('button, a')].find(b => /LIME/.test(b.textContent)), '2. CLICK  LIME →', 'top');
  `)

  // 2. Live explanation for 2025-01-25
  await shot('g02_live_explanation.png', `${XAI}/anomaly-diagnosis?source=bi&date=2025-01-25`, has('Live LIME Explanation'), `
    __mark(document.querySelector('.lad-pred-row'), 'Actual vs predicted: almost the same', 'top');
    __mark(document.querySelector('.lad-contrib-row'), 'Temperature above 29.3 °C: +359 kW', 'bottom');
  `)
  await shot('g03_live_r2_and_total.png', `${XAI}/anomaly-diagnosis?source=bi&date=2025-01-25`, has('Live LIME Explanation'), `
    document.querySelector('.lad-conf').scrollIntoView({ block: 'start' }); window.scrollBy(0, -90); ${pause(300)}
    __mark(document.querySelector('.lad-conf'), 'LIME fit (R²) = 0.59', 'top');
  `)

  // 3. Page 01
  await shot('g04_page01_top.png', `${XAI}/temporal-drift`, has('Temperature dominates'), `
    __mark(document.querySelector('.cards-row'), 'Summary cards', 'top');
    __mark(document.querySelector('.dominance-note'), 'Read this note', 'bottom');
  `)
  await shot('g05_page01_toggle.png', `${XAI}/temporal-drift`, has('Temperature dominates'), `
    document.querySelector('.feature-toggles').scrollIntoView({ block: 'start' }); document.querySelector('.main')?.scrollBy?.(0, -10); ${pause(300)}
    __mark(__byText('.feature-toggles .toggle-btn', 'Temperature'), 'CLICK to show / hide Temperature', 'right');
  `)
  await shot('g06_page01_comparison.png', `${XAI}/temporal-drift`, has('Forecasting Model Comparison'), `
    const sec = __byText('.section-title', 'Forecasting Model Comparison').closest('.section');
    sec.scrollIntoView({ block: 'start' }); ${pause(300)}
    __mark(sec.querySelector('.cmp-row--explained'), 'My model: XGBoost', 'bottom');
  `)

  // 4. Page 02
  await shot('g07_page02_peak.png', `${XAI}/anomaly-diagnosis`, has('Feature Contributions'), `
    const pill = __byText('.lad-filter-pill', 'Peak'); pill.click(); ${pause(500)}
    const card = __byText('.lad-instance-card', '#15'); card.click(); ${pause(600)}
    __mark(__byText('.lad-filter-pill', 'Peak'), '1. CLICK Peak', 'top');
    __mark(__byText('.lad-instance-card', '#15'), '2. CLICK #15', 'right');
    __mark(document.querySelector('.lad-panel--detail .lad-contrib-row'), '3. Temperature +353 kW', 'top');
  `)
  await shot('g08_page02_medium.png', `${XAI}/anomaly-diagnosis`, has('Feature Contributions'), `
    __byText('.lad-filter-pill', 'Medium').click(); ${pause(500)}
    __byText('.lad-instance-card', '#04').click(); ${pause(600)}
    __mark(__byText('.lad-filter-pill', 'Medium'), '1. CLICK Medium', 'top');
    __mark(__byText('.lad-instance-card', '#04'), '2. CLICK #04', 'right');
    __mark(document.querySelector('.lad-panel--detail .lad-conf'), '3. Low fit: R² = 0.04', 'bottom');
  `)

  // 5. Page 03
  await shot('g09_page03_intro.png', `${XAI}/model-xai-comparison`, has('A · Forecasting models'), `
    __mark(document.querySelector('.mx-intro'), 'Read this first', 'bottom');
  `)
  await shot('g10_page03_models.png', `${XAI}/model-xai-comparison`, has('A · Forecasting models'), `
    const t = __byText('.section-title', 'A · Forecasting models').closest('.section');
    t.scrollIntoView({ block: 'start' }); ${pause(300)}
    __mark(t.querySelector('.cmp-row--explained'), 'XGBoost: about 2 kW error', 'bottom');
  `)
  await shot('g11_page03_shap_vs_lime.png', `${XAI}/model-xai-comparison`, has('B · SHAP vs LIME'), `
    const s = __byText('.section-title', 'B · SHAP vs LIME').closest('.section');
    s.querySelector('.table-box').scrollIntoView({ block: 'start' }); ${pause(300)}
    __mark(s.querySelector('.table-box tbody tr'), 'SHAP 99.9% vs LIME 70%', 'top');
  `)
  await shot('g12_page03_shap_proof.png', `${XAI}/model-xai-comparison`, has('B · SHAP vs LIME'), `
    const img = document.querySelector('img[src*="shap_dependence_temperature"]');
    img.scrollIntoView({ block: 'center' }); ${pause(800)}
    __mark(img, 'Dots on the line = SHAP is correct', 'top');
  `)
  await shot('g13_page03_lime_stability.png', `${XAI}/model-xai-comparison`, has('B · SHAP vs LIME'), `
    const img = document.querySelector('img[src*="lime_stability_box"]');
    img.scrollIntoView({ block: 'center' }); ${pause(800)}
    __mark(img, 'LIME changes a little with each seed', 'top');
  `)
  await shot('g14_page03_drift.png', `${XAI}/model-xai-comparison`, has('C · Temporal drift'), `
    const img = document.querySelector('img[src*="temporal_drift_v2"]');
    img.scrollIntoView({ block: 'center' }); ${pause(800)}
    __mark(img, 'Shaded band = 95% confidence interval', 'top');
  `)

  // 6. Swagger: run /api/explain-date for 2025-01-25 with REAL mouse clicks
  // and typing (Swagger's React inputs ignore values set from script).
  async function realClick(selectorExpr) {
    const r = await evaluate(`(() => { const e = ${selectorExpr}; e.scrollIntoView({ block: 'center' });
      const b = e.getBoundingClientRect(); return { x: b.left + b.width / 2, y: b.top + b.height / 2 } })()`)
    await sleep(250)
    for (const type of ['mousePressed', 'mouseReleased']) {
      await send('Input.dispatchMouseEvent', { type, x: r.x, y: r.y, button: 'left', clickCount: 1 })
    }
    await sleep(400)
  }
  async function swaggerRun(execute = true) {
    await send('Page.navigate', { url: 'http://127.0.0.1:8000/docs' })
    await waitFor(`document.readyState === 'complete'`)
    await waitFor(has('/api/explain-date'))
    await evaluate(MARKER)
    const block = `[...document.querySelectorAll('.opblock')].find(b => b.textContent.includes('/api/explain-date'))`
    await realClick(`${block}.querySelector('.opblock-summary-control') || ${block}.querySelector('.opblock-summary')`)
    await waitFor(`Boolean(${block}.querySelector('.try-out__btn'))`)
    await realClick(`${block}.querySelector('.try-out__btn')`)
    await waitFor(`Boolean(${block}.querySelector('.parameters input'))`)
    await realClick(`${block}.querySelector('.parameters input')`)
    await send('Input.insertText', { text: '2025-01-25' })
    await sleep(300)
    if (!execute) return block
    await realClick(`${block}.querySelector('.execute')`)
    await waitFor(`Boolean(${block}.querySelector('.live-responses-table'))`, 20000)
    await sleep(800)
    return block
  }
  async function swaggerShot(name, marks, execute = true) {
    try {
      const block = await swaggerRun(execute)
      await evaluate(`(async () => { const block = ${block}; ${marks} })()`)
      await sleep(500)
      const res = await send('Page.captureScreenshot', { format: 'png' })
      writeFileSync(join(OUT, name), Buffer.from(res.result.data, 'base64'))
      console.log('OK   ' + name)
    } catch (e) {
      failures++
      console.log('FAIL ' + name + ': ' + e.message)
    }
  }
  await swaggerShot('g15_swagger_explain_date.png', `
    const input = block.querySelector('.parameters input');
    input.scrollIntoView({ block: 'start' }); window.scrollBy(0, -90); ${pause(300)}
    __mark(input, '1. Type 2025-01-25', 'right');
    __mark(block.querySelector('.execute'), '2. CLICK Execute', 'right');
  `, false)
  await swaggerShot('g16_swagger_response.png', `
    const live = block.querySelector('.live-responses-table');
    live.scrollIntoView({ block: 'start' }); window.scrollBy(0, -40); ${pause(300)}
    __mark(live.querySelector('.response-col_status'), 'Code 200 = OK', 'right');
    __mark(live.querySelector('.highlight-code, .microlight, pre'), 'The explanation as data (JSON)', 'top');
  `)
  ws.close()
} finally {
  edge.kill()
}
process.exitCode = failures ? 1 : 0
