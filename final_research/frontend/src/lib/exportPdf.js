import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import { fmtHour, fmtKw, fmtSigned, FEATURE_LABEL } from './labels.js';

// jsPDF's built-in fonts cover Latin-1 only: swap or drop anything outside it.
const clean = (t) => String(t)
  .replace(/[−–—]/g, '-').replace(/→/g, '->').replace(/…/g, '...')
  .replace(/[^\x20-\x7E -ÿ\n]/g, '').replace(/ +/g, ' ').trim();

async function snap(el) {
  const prevAlign = el.style.alignSelf;
  el.style.alignSelf = 'start'; // stop grid rows stretching the card, so no blank space is captured
  const canvas = await html2canvas(el, {
    scale: 1.5, backgroundColor: '#ffffff', logging: false,
    // capture the card at its content height and un-clip truncated labels
    onclone: (doc) => {
      const c = doc.getElementById(el.id);
      if (!c) return;
      c.style.height = 'auto';
      c.querySelectorAll('.truncate').forEach((n) => { n.style.overflow = 'visible'; n.style.textOverflow = 'clip'; });
    },
  });
  el.style.alignSelf = prevAlign;
  return { data: canvas.toDataURL('image/jpeg', 0.85), w: canvas.width, h: canvas.height };
}

export async function exportScenarioPdf({ base, scen, head, status, capacity, peakKw, peakHour, hour, recs, explain, ref, changes }) {
  const doc = new jsPDF({ unit: 'mm', format: 'a4' });
  const W = 210, M = 15, CW = W - 2 * M;
  let y = M;
  const ensure = (h) => { if (y + h > 285) { doc.addPage(); y = M; } };
  const text = (t, size = 10, style = 'normal', color = [30, 41, 59], gap = 1.5) => {
    doc.setFont('helvetica', style); doc.setFontSize(size); doc.setTextColor(...color);
    const lines = doc.splitTextToSize(clean(t), CW);
    ensure(lines.length * size * 0.42 + gap);
    doc.text(lines, M, y + size * 0.35);
    y += lines.length * size * 0.42 + gap;
  };

  // Title band
  doc.setFillColor(79, 70, 229); doc.rect(0, 0, W, 28, 'F');
  doc.setTextColor(255, 255, 255); doc.setFont('helvetica', 'bold'); doc.setFontSize(18);
  doc.text('Electricity Demand: What-If Report', M, 14);
  doc.setFont('helvetica', 'normal'); doc.setFontSize(10);
  doc.text(`Generated ${new Date().toLocaleString()}  |  Focus hour: ${fmtHour(hour)}`, M, 21);
  y = 36;

  text('What this means', 13, 'bold', [79, 70, 229], 2);
  text(head.text, 11, 'normal', [15, 23, 42], 4);

  // Grid status box
  const col = status.key === 'overload' ? [220, 38, 38] : status.key === 'watch' ? [217, 119, 6] : [5, 150, 105];
  ensure(18);
  doc.setDrawColor(...col); doc.setLineWidth(0.6); doc.roundedRect(M, y, CW, 14, 2, 2);
  doc.setFont('helvetica', 'bold'); doc.setFontSize(12); doc.setTextColor(...col);
  doc.text(clean(`Grid status: ${status.label}`), M + 4, y + 6);
  doc.setFont('helvetica', 'normal'); doc.setFontSize(10); doc.setTextColor(51, 65, 85);
  doc.text(clean(`Peak ${fmtKw(peakKw)} at ${fmtHour(peakHour)} vs supply limit ${capacity} kW (${Math.round(status.ratio * 100)}%)`), M + 4, y + 11);
  y += 20;

  // Inputs table
  text('Scenario inputs', 13, 'bold', [79, 70, 229], 2);
  const rows = [
    ['Temperature', `${base.temp.toFixed(1)} C`, `${scen.temp.toFixed(1)} C`],
    ['Humidity', `${Math.round(base.humidity)} %`, `${Math.round(scen.humidity)} %`],
    ['Electricity price', `${base.price.toFixed(1)} LKR/kWh`, `${scen.price.toFixed(1)} LKR/kWh`],
    ['Economic activity', 'baseline', `${scen.gdp >= base.gdp ? '+' : '-'}${Math.abs((scen.gdp / base.gdp - 1) * 100).toFixed(0)} %`],
  ];
  doc.setFont('helvetica', 'bold'); doc.setFontSize(9); doc.setTextColor(100, 116, 139);
  ensure(30);
  doc.text('Factor', M, y + 3); doc.text('Normal day', M + 70, y + 3); doc.text('Your what-if', M + 120, y + 3);
  y += 6; doc.setFont('helvetica', 'normal'); doc.setFontSize(10); doc.setTextColor(30, 41, 59);
  rows.forEach(([a, b, c]) => { doc.setDrawColor(226, 232, 240); doc.line(M, y, M + CW, y); doc.text(a, M, y + 5); doc.text(b, M + 70, y + 5); doc.text(c, M + 120, y + 5); y += 7; });
  y += 4;

  // Chart + drivers as pictures of what is on screen
  for (const id of ['chart-card', 'drivers-card']) {
    const el = document.getElementById(id);
    if (!el) continue;
    const img = await snap(el);
    const h = (CW * img.h) / img.w;
    ensure(h + 4);
    doc.addImage(img.data, 'JPEG', M, y, CW, h); y += h + 6;
  }

  text('Suggested actions', 13, 'bold', [79, 70, 229], 2);
  recs.forEach((r) => { text(r.title, 10.5, 'bold', [15, 23, 42], 0.5); text(r.body, 10, 'normal', [71, 85, 105], 3); });

  // Footer: model facts and honest disclosure
  y += 2;
  const perf = ref.performance || {};
  text('About the forecast', 11, 'bold', [79, 70, 229], 1.5);
  text(`Model: ${ref.model_type}. Test accuracy R2 = ${perf.test_r2?.toFixed(3)}, average error about ${Math.round(perf.test_mae)} kW. ` +
    'Effects are one-factor-at-a-time estimates from the model. They show likely direction and size, not guarantees.', 9, 'normal', [100, 116, 139], 2);
  text('Data note: this project uses a synthetic dataset (practice work); figures illustrate the method and are not real grid measurements.', 9, 'italic', [100, 116, 139]);

  doc.save(`demand-whatif-${new Date().toISOString().slice(0, 10)}.pdf`);
}
