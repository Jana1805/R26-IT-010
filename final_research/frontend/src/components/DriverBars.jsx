import React, { useState } from 'react';
import { Card, Chip } from './Card.jsx';
import { FEATURE_LABEL, featureValueText, fmtHour, fmtKw, fmtSigned } from '../lib/labels.js';

function Bars({ rows, max }) {
  return (
    <ul className="space-y-2">
      {rows.map((r) => {
        const w = Math.max(2, (Math.abs(r.effect) / max) * 50);
        const up = r.effect >= 0;
        return (
          <li key={r.key} className="grid grid-cols-[minmax(0,9rem)_1fr_4.5rem] items-center gap-2 text-sm">
            <span className="truncate text-slate-700" title={r.sub}>{r.label}</span>
            <div className="relative h-5">
              <span className="absolute left-1/2 top-0 h-5 w-px bg-slate-300" />
              <span className="absolute top-0.5 h-4 rounded" style={{ width: `${w}%`, background: up ? '#f43f5e' : '#10b981', ...(up ? { left: '50%' } : { right: '50%' }) }} />
            </div>
            <span className={`text-right font-semibold ${up ? 'text-rose-600' : 'text-emerald-600'}`}>{fmtSigned(r.effect)} kW</span>
          </li>
        );
      })}
    </ul>
  );
}

export default function DriverBars({ explain }) {
  const [mode, setMode] = useState('change');
  if (!explain) return <Card id="drivers-card" title="Why is demand like this?"><p className="text-sm text-slate-500">Loading…</p></Card>;
  const toRow = (d, from) => ({
    key: d.feature,
    label: FEATURE_LABEL[d.feature]?.name || d.feature,
    sub: from ? `${featureValueText(d.feature, d.from)} → ${featureValueText(d.feature, d.to)}` : `${featureValueText(d.feature, d.value)} vs usual ${featureValueText(d.feature, d.typical)}`,
    effect: d.effect_kw,
  });
  const change = explain.change_drivers.map((d) => toRow(d, true));
  if (Math.abs(explain.interaction_kw) >= 1) change.push({ key: 'interaction', label: 'Combined effect', sub: 'Extra effect when several changes act together', effect: explain.interaction_kw });
  const level = explain.level_drivers.map((d) => toRow(d, false));
  const rows = mode === 'change' ? change : level;
  const max = Math.max(1, ...rows.map((r) => Math.abs(r.effect)));
  return (
    <Card id="drivers-card" title="Why is demand like this?" subtitle={`Each bar shows how many kW that factor adds (red) or removes (green) at ${fmtHour(explain.hour)}.`}>
      <div className="mb-3 flex flex-wrap gap-2">
        <Chip active={mode === 'change'} onClick={() => setMode('change')}>What changed vs normal day</Chip>
        <Chip active={mode === 'level'} onClick={() => setMode('level')}>What sets this day apart</Chip>
      </div>
      {rows.length === 0 ? (
        <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">Nothing differs from the normal day yet. Move a slider to see which factor drives the change.</p>
      ) : <Bars rows={rows} max={max} />}
      <p className="mt-3 text-xs text-slate-400">
        Method: each factor is changed on its own while the rest stay fixed, and the model's answer is compared (a simple what-if attribution).
        {mode === 'change' ? ` Normal ${fmtKw(explain.baseline_kw)} → what-if ${fmtKw(explain.scenario_kw)}.` : ` Typical day ${fmtKw(explain.typical_kw)}.`}
      </p>
    </Card>
  );
}
