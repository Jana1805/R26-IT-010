// Exports a viva Markdown file to an A4 PDF next to it, with images (diagrams)
// embedded. Renders Markdown with marked 12.0.2 (jsDelivr) in headless
// Microsoft Edge and prints via the DevTools protocol. Needs internet for marked.
//
//   node viva/tools/export_pdf.mjs                               (HANDOVER_FOR_MADUSHANI.md)
//   node viva/tools/export_pdf.mjs viva/VIVA_NOTES.md            (any other viva .md)
//   node viva/tools/export_pdf.mjs viva/SIMPLE_PRESENTATION_GUIDE.md --large   (14pt large print)
// In the Markdown, <div class="pb"></div> forces a page break and
// <div class="cheat"> … </div> makes a large-text cheat sheet.
import { spawn } from 'node:child_process'
import { readFileSync, writeFileSync, mkdtempSync } from 'node:fs'
import { join, dirname, resolve, basename } from 'node:path'
import { tmpdir } from 'node:os'
import { fileURLToPath, pathToFileURL } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const args = process.argv.slice(2)
const LARGE = args.includes('--large')
const SRC = resolve(args.find(a => !a.startsWith('--')) || join(HERE, '..', 'HANDOVER_FOR_MADUSHANI.md'))
const OUT = SRC.replace(/\.md$/i, '.pdf')
const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
const PORT = 9344
const sleep = ms => new Promise(r => setTimeout(r, ms))

const css = `
  @page { size: A4; margin: 13mm 13mm 15mm 13mm; }
  body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 9.6pt; line-height: 1.4; color: #1b1b1b; }
  h1 { font-size: 19pt; margin: 0 0 6pt; color: #0d366b; }
  h2 { font-size: 13pt; margin: 14pt 0 5pt; padding-bottom: 3pt; border-bottom: 1.5px solid #2a78d6; color: #0d366b; break-after: avoid; }
  p:has(+ blockquote), p:has(+ pre), p:has(+ table), p:has(+ ul), p:has(+ ol) { break-after: avoid; }
  h3 { font-size: 11.5pt; margin: 12pt 0 4pt; break-after: avoid; }
  p, li { orphans: 3; widows: 3; }
  ul, ol { margin: 4pt 0 6pt; padding-left: 18pt; }
  li { margin: 2pt 0; }
  table { border-collapse: collapse; width: 100%; margin: 5pt 0 8pt; font-size: 8.6pt; }
  th, td { border: 1px solid #c9c8c2; padding: 2.5pt 4.5pt; vertical-align: top; text-align: left; }
  th { background: #e8f1fd; }
  tr { break-inside: avoid; }
  code { font-family: Consolas, 'Courier New', monospace; font-size: 8.8pt; background: #f2f2ef; padding: 0 2pt; border-radius: 2px; }
  pre { background: #f2f2ef; padding: 6pt 8pt; border-radius: 4px; white-space: pre-wrap; break-inside: avoid; }
  pre code { background: none; padding: 0; }
  blockquote { margin: 6pt 0; padding: 6pt 10pt; border-left: 4px solid #2a78d6; background: #f3f7fd; break-inside: avoid; }
  img { display: block; width: 100%; height: auto; max-height: 200mm; object-fit: contain; margin: 4pt auto 8pt; break-inside: avoid; }
  hr { border: none; border-top: 1px solid #dddcd6; margin: 12pt 0; }
  a { color: #1c5cab; text-decoration: none; }
  /* Forced break goes BEFORE the next element, so a full page never yields a blank one */
  .pb { display: none; }
  .pb + * { break-before: page; }
  body { font-family: 'Segoe UI', 'Segoe UI Emoji', Arial, sans-serif; }
`
// Large print: ~14pt text, generous spacing, screenshots kept with their step.
const cssLarge = `
  @page { size: A4; margin: 16mm 16mm 18mm 16mm; }
  body { font-size: 14pt; line-height: 1.6; }
  h1 { font-size: 26pt; margin-bottom: 10pt; }
  h2 { font-size: 20pt; margin: 4pt 0 12pt; }
  h3 { font-size: 16pt; margin: 18pt 0 8pt; color: #0d366b; }
  p { margin: 8pt 0; }
  li { margin: 5pt 0; }
  table { font-size: 12pt; }
  th, td { padding: 5pt 7pt; }
  code { font-size: 12pt; }
  pre { font-size: 12pt; }
  blockquote { font-size: 14.5pt; padding: 8pt 12pt; margin: 10pt 0; background: #fff6e8; border-left-color: #d95926; }
  img { max-height: 118mm; border: 1px solid #c9c8c2; border-radius: 4px; margin: 8pt auto 10pt; }
  input[type=checkbox] { width: 14pt; height: 14pt; vertical-align: -2pt; margin-right: 6pt; }
  ul:has(input[type=checkbox]) { list-style: none; padding-left: 4pt; }
  .cheat { font-size: 17pt; line-height: 1.55; border: 3px solid #2a78d6; border-radius: 10px; padding: 6pt 16pt 10pt; break-inside: avoid; }
  .cheat h2 { font-size: 22pt; border-bottom: none; margin-top: 6pt; }
  .cheat li { margin: 3pt 0; }
`
const md = readFileSync(SRC, 'utf8')
const html = `<!doctype html><html><head><meta charset="utf-8">
<base href="${pathToFileURL(dirname(SRC)).href}/">
<title>${basename(SRC, '.md')}</title><style>${css}${LARGE ? cssLarge : ''}</style>
<script src="https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"></script></head>
<body><div id="doc"></div>
<script>
  const md = ${JSON.stringify(md)};
  document.getElementById('doc').innerHTML = marked.parse(md, { gfm: true });
  window.__ready = Promise.all([...document.images].map(i => i.complete ? 1 :
    new Promise(r => { i.onload = i.onerror = r })));
</script></body></html>`
const tmp = mkdtempSync(join(tmpdir(), 'viva-pdf-'))
const page = join(tmp, 'doc.html')
writeFileSync(page, html)

const edge = spawn(EDGE, ['--headless=new', '--disable-gpu', '--no-first-run', '--allow-file-access-from-files',
  `--user-data-dir=${join(tmp, 'profile')}`, `--remote-debugging-port=${PORT}`, 'about:blank'], { stdio: 'ignore' })
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
  const evaluate = async expr => (await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true })).result?.result?.value

  await send('Page.enable')
  await send('Page.navigate', { url: pathToFileURL(page).href })
  let ready = false
  for (let i = 0; i < 300 && !ready; i++) {   // up to 60 s for marked from the CDN
    ready = await evaluate('typeof marked !== "undefined" && document.getElementById("doc").children.length > 0')
    if (!ready) await sleep(200)
  }
  if (!ready) throw new Error('marked did not load from jsDelivr within 60 s (no internet?)')
  await evaluate('window.__ready.then(() => true)')
  const broken = await evaluate('[...document.images].filter(i => !i.naturalWidth).map(i => i.getAttribute("src"))')
  if (broken.length) throw new Error('images not found: ' + broken.join(', '))

  const res = await send('Page.printToPDF', {
    printBackground: true, preferCSSPageSize: true, displayHeaderFooter: true,
    headerTemplate: '<span></span>',
    footerTemplate: `<div style="font-size:8px;color:#777;width:100%;padding:0 15mm;display:flex;justify-content:space-between;font-family:Segoe UI,Arial">
      <span>${basename(SRC, '.md').replace(/_/g, ' ')}</span>
      <span>page <span class="pageNumber"></span> of <span class="totalPages"></span></span></div>`,
  })
  writeFileSync(OUT, Buffer.from(res.result.data, 'base64'))
  const pages = (readFileSync(OUT, 'latin1').match(/\/Type\s*\/Page[^s]/g) || []).length
  console.log(`saved ${OUT} (${pages} pages, ${(readFileSync(OUT).length / 1024).toFixed(0)} KB)`)
  ws.close()
} finally {
  edge.kill()
}
