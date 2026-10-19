import React from 'react';
import { Card } from './Card.jsx';
import { fmtKw, fmtHour } from '../lib/labels.js';

export default function StatusGauge({ peakKw, peakHour, capacity, onCapacity, status, min, max }) {
  const pct = Math.min(130, (peakKw / capacity) * 100);
  const arc = (a0, a1, color) => {
    const r = 80, cx = 100, cy = 100;
    const [x0, y0] = [cx + r * Math.cos(Math.PI * (1 - a0 / 130)), cy - r * Math.sin(Math.PI * (1 - a0 / 130))];
    const [x1, y1] = [cx + r * Math.cos(Math.PI * (1 - a1 / 130)), cy - r * Math.sin(Math.PI * (1 - a1 / 130))];
    return <path d={`M ${x0} ${y0} A ${r} ${r} 0 0 1 ${x1} ${y1}`} stroke={color} strokeWidth="16" fill="none" />;
  };
  const needle = (() => {
    const t = Math.PI * (1 - pct / 130);
    return [100 + 70 * Math.cos(t), 100 - 70 * Math.sin(t)];
  })();
  return (
    <Card id="status-card" step="3" title="So what? Can the grid cope?" subtitle="Peak demand compared with how much power we can supply.">
      <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-center">
        <svg viewBox="0 0 200 124" className="w-56 shrink-0" role="img" aria-label={`Grid status: ${status.label}`}>
          {arc(0, 85, '#10b981')}{arc(85, 100, '#f59e0b')}{arc(100, 130, '#ef4444')}
          <line x1="100" y1="100" x2={needle[0]} y2={needle[1]} stroke="#0f172a" strokeWidth="4" strokeLinecap="round" />
          <circle cx="100" cy="100" r="7" fill="#0f172a" />
          <text x="100" y="119" textAnchor="middle" fontSize="11" fill="#475569">{Math.round((peakKw / capacity) * 100)}% of supply</text>
        </svg>
        <div className="flex-1 text-center sm:text-left">
          <span className="inline-block rounded-full px-3 py-1 text-sm font-bold" style={{ color: status.color, background: status.bg }}>{status.label}</span>
          <p className="mt-2 text-slate-700">Highest demand of the day: <b>{fmtKw(peakKw)}</b> at <b>{fmtHour(peakHour)}</b>.</p>
          <label className="mt-3 block text-sm text-slate-600">Supply limit: <b>{capacity} kW</b>
            <input type="range" min={min} max={max} step={50} value={capacity} onChange={(e) => onCapacity(Number(e.target.value))} className="mt-1 block w-full accent-red-500" />
          </label>
          <p className="text-xs text-slate-400">Slide to test a smaller or larger power supply.</p>
        </div>
      </div>
    </Card>
  );
}
