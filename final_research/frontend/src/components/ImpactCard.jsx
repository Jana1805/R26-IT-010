import React from 'react';
import { fmtKw, fmtSigned } from '../lib/labels.js';

export default function ImpactCard({ head, scenKw, baseKw }) {
  const up = head.diff >= 0;
  const color = Math.abs(head.diff) < 1 ? 'text-slate-600' : up ? 'text-rose-600' : 'text-emerald-600';
  return (
    <div id="impact-card" className="rounded-2xl bg-gradient-to-br from-indigo-600 to-violet-600 p-5 text-white shadow-panel sm:p-6">
      <p className="text-sm uppercase tracking-wide text-indigo-100">What this means</p>
      <p className="mt-2 text-lg font-medium leading-snug sm:text-xl">{head.text}</p>
      <div className="mt-4 grid grid-cols-3 gap-3 text-center">
        <div className="rounded-xl bg-white/15 p-3"><p className="text-xs text-indigo-100">Normal</p><p className="text-lg font-bold">{fmtKw(baseKw)}</p></div>
        <div className="rounded-xl bg-white/15 p-3"><p className="text-xs text-indigo-100">Your what-if</p><p className="text-lg font-bold">{fmtKw(scenKw)}</p></div>
        <div className="rounded-xl bg-white p-3"><p className="text-xs text-slate-500">Change</p>
          <p className={`text-lg font-bold ${color}`}>{fmtSigned(head.diff)} kW <span className="text-xs">({fmtSigned(head.pct, 1)}%)</span></p></div>
      </div>
    </div>
  );
}
