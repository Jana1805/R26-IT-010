// Captures backup screenshots of every XAI page, Swagger, and the BI dashboard
// row with the "LIME →" button, into viva/screenshots/. The system must be
// running first (python start-all.py). Uses headless Microsoft Edge via the
// DevTools protocol; Node 22+.
//
//   node viva/tools/capture_screenshots.mjs        (from madushani_xai/)
import { spawn } from 'node:child_process'
import { mkdirSync, writeFileSync, mkdtempSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { tmpdir } from 'node:os'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const OUT = join(HERE, '..', 'screenshots')
const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
const PORT = 9343
const W = 1440, H = 900, SCALE = 1.5
const sleep = ms => new Promise(r => setTimeout(r, ms))
mkdirSync(OUT, { recursive: true })

const edge = spawn(EDGE, ['--headless=new', '--disable-gpu', '--no-first-run', '--hide-scrollbars',
  `--user-data-dir=${mkdtempSync(join(tmpdir(), 'viva-shots-'))}`,
  `--remote-debugging-port=${PORT}`, 'about:blank'], { stdio: 'ignore' })

let failures = 0
try {
  let wsUrl
  for (let i = 0; i < 40 && !wsUrl; i++) {
    try {
      wsUrl = (await (await fetch(`http://127.0.0.1:${PORT}/json`)).json()).find(t => t.type === 'page')?.webSocketDebuggerUrl
    } catch { await sleep(300) }
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
  const evaluate = async expr => (await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true })).result?.result?.value
  const waitFor = async (expr, ms = 25000) => {
    for (const t0 = Date.now(); Date.now() - t0 < ms;) { if (await evaluate(expr)) return true; await sleep(300) }
    return false
  }
  // Only images inside the viewport must be loaded (lazy ones below it never load)
  const imagesLoaded = `[...document.images].filter(i => i.getBoundingClientRect().top < innerHeight)
                          .every(i => i.complete && i.naturalWidth > 0)`
  // The dashboards scroll inside a container, so measure the tallest scrolling element
  const contentHeight = `Math.ceil(Math.max(...[...document.querySelectorAll('*')].map(e => e.scrollHeight)))`

  await send('Page.enable')
  await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: SCALE, mobile: false })

  // Case-insensitive text check: innerText follows CSS text-transform.
  const hasText = t => `document.body.innerText.toLowerCase().includes(${JSON.stringify(t.toLowerCase())})`

  async function shot(name, url, readyExpr, { fullPage = false, scrollExpr = null } = {}) {
    await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: SCALE, mobile: false })
    await send('Page.navigate', { url })
    let ok = await waitFor(readyExpr)
    if (fullPage) {
      // Grow the viewport to the whole page so lazy-loaded figures load too
      const h = await evaluate(contentHeight)
      await send('Emulation.setDeviceMetricsOverride', { width: W, height: h, deviceScaleFactor: SCALE, mobile: false })
    }
    if (scrollExpr) await evaluate(scrollExpr)
    ok = ok && await waitFor(imagesLoaded)
    await sleep(1000)   // let charts finish their entry animation
    const res = await send('Page.captureScreenshot', { format: 'png' })
    writeFileSync(join(OUT, name), Buffer.from(res.result.data, 'base64'))
    console.log(`${ok ? 'OK  ' : 'WARN'} ${name}${ok ? '' : ' (page content not confirmed)'}`)
    if (!ok) failures++
  }

  const XAI = 'http://localhost:5173'
  const biRow = `[...document.querySelectorAll('tr')].find(r => r.textContent.includes('2025-01-25'))`
  await shot('01_xai_temporal_drift.png', `${XAI}/temporal-drift`, hasText('Forecasting Model Comparison'), { fullPage: true })
  await shot('01a_xai_temporal_drift_top.png', `${XAI}/temporal-drift`, hasText('Temperature dominates'))
  await shot('02_xai_lime_list.png', `${XAI}/anomaly-diagnosis`, hasText('Feature Contributions'))
  await shot('03_xai_lime_live_2025-01-25.png', `${XAI}/anomaly-diagnosis?source=bi&date=2025-01-25`,
    hasText('Live LIME Explanation'), { fullPage: true })
  await shot('04_xai_model_xai_comparison.png', `${XAI}/model-xai-comparison`, hasText('C · Temporal drift'), { fullPage: true })
  await shot('04a_xai_model_xai_comparison_top.png', `${XAI}/model-xai-comparison`, hasText('A · Forecasting models'))
  await shot('05_xai_swagger_docs.png', 'http://127.0.0.1:8000/docs', hasText('/api/explain-date'), { fullPage: true })
  await shot('06_bi_dashboard.png', 'http://localhost:3000', `Boolean(${biRow})`)
  // The abnormal-days table scrolled so the 2025-01-25 row and its "LIME →" button sit mid-screen
  await shot('07_bi_lime_button_row_2025-01-25.png', 'http://localhost:3000', `Boolean(${biRow})`,
    { scrollExpr: `${biRow}.scrollIntoView({ block: 'center' })` })
  ws.close()
} finally {
  edge.kill()
}
process.exitCode = failures ? 1 : 0
