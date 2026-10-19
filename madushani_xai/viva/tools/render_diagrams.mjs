// Renders every viva/diagrams/*.mmd to a PNG next to it, using headless
// Microsoft Edge (DevTools protocol) and Mermaid 10.9.1 from jsDelivr.
// Needs internet for the Mermaid script. Node 22+ (built-in fetch/WebSocket).
//
//   node viva/tools/render_diagrams.mjs            (from madushani_xai/)
import { spawn } from 'node:child_process'
import { readdirSync, readFileSync, writeFileSync, mkdtempSync } from 'node:fs'
import { join, dirname, basename } from 'node:path'
import { tmpdir } from 'node:os'
import { fileURLToPath, pathToFileURL } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const DIAGRAMS = join(HERE, '..', 'diagrams')
const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
const PORT = 9341
const SCALE = 2 // 2x pixels so text stays sharp on a projector
const sleep = ms => new Promise(r => setTimeout(r, ms))

const edge = spawn(EDGE, ['--headless=new', '--disable-gpu', '--no-first-run',
  `--user-data-dir=${mkdtempSync(join(tmpdir(), 'viva-edge-'))}`,
  `--remote-debugging-port=${PORT}`, '--window-size=2400,2000', 'about:blank'], { stdio: 'ignore' })

try {
  let wsUrl
  for (let i = 0; i < 40 && !wsUrl; i++) {
    try {
      const tabs = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json()
      wsUrl = tabs.find(t => t.type === 'page')?.webSocketDebuggerUrl
    } catch { await sleep(300) }
  }
  if (!wsUrl) throw new Error('Edge DevTools not reachable')

  const ws = new WebSocket(wsUrl)
  await new Promise(r => ws.addEventListener('open', r, { once: true }))
  let id = 0
  const pending = new Map()
  ws.addEventListener('message', e => {
    const m = JSON.parse(e.data)
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) }
  })
  const send = (method, params = {}) => new Promise(r => {
    const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params }))
  })
  const evaluate = async expr => {
    const res = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true })
    if (res.result?.exceptionDetails) throw new Error(JSON.stringify(res.result.exceptionDetails))
    return res.result?.result?.value
  }

  await send('Page.enable')
  await send('Emulation.setDeviceMetricsOverride', { width: 2400, height: 2000, deviceScaleFactor: 1, mobile: false })
  await send('Page.navigate', { url: pathToFileURL(join(HERE, 'render.html')).href })
  let ready = false
  for (let i = 0; i < 300 && !ready; i++) {   // up to 60 s for the 3 MB Mermaid script
    ready = await evaluate('typeof window.renderDiagram === "function" && typeof mermaid !== "undefined"')
    if (!ready) await sleep(200)
  }
  if (!ready) throw new Error('Mermaid did not load from jsDelivr within 60 s (no internet?)')

  for (const file of readdirSync(DIAGRAMS).filter(f => f.endsWith('.mmd')).sort()) {
    const src = readFileSync(join(DIAGRAMS, file), 'utf8')
    const box = await evaluate(`window.renderDiagram(${JSON.stringify(src)})`)
    const shot = await send('Page.captureScreenshot', {
      format: 'png', captureBeyondViewport: true,
      clip: { x: box.x, y: box.y, width: box.width, height: box.height, scale: SCALE },
    })
    const out = join(DIAGRAMS, basename(file, '.mmd') + '.png')
    writeFileSync(out, Buffer.from(shot.result.data, 'base64'))
    console.log(`rendered ${file} -> ${basename(out)} (${box.width * SCALE} x ${box.height * SCALE} px)`)
  }
  ws.close()
} finally {
  edge.kill()
}
