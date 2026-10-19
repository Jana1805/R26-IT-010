import React from 'react';
import { Card } from './Card.jsx';
import { FEATURE_LABEL, featureValueText, fmtHour, fmtKw } from '../lib/labels.js';

// Each bar spans the demand you would see at the factor's usual low and high values
// (all other inputs held at the current what-if), on one shared kW axis.
export default function Tornado({ data }) {
  if (!data) return null;
  const rows = data.factors.slice(0, 6);
  const vals = rows.flatMap((r) => [r.at_low_kw, r.at_high_kw]).concat(data.current_kw);
  const lo = Math.floor((Math.min(...vals) - 20) / 50) * 50, hi = Math.ceil((Math.max(...vals) + 20) / 50) * 50;
  const pos = (v) => `${((v - lo) / (hi - lo)) * 100}%`;
  return (
    <Card id="tornado-card" title="What matters most?" subtitle={`How far each factor alone can push demand at ${fmtHour(data.hour)}, from its usual low to its usual high. Longer bar = bigger influence.`}>
      <ul className="space-y-3">
        {rows.map((r) => {
          const a = Math.min(r.at_low_kw, r.at_high_kw), b = Math.max(r.at_low_kw, r.at_high_kw);
          return (
            <li key={r.feature} className="text-sm">
              <div className="mb-1 flex justify-between"><span className="font-medium text-slate-800">{FEATURE_LABEL[r.feature]?.name}</span><span className="text-slate-500">swing {fmtKw(r.swing_kw)}</span></div>
              <div className="relative h-5 rounded bg-slate-100">
                <span className="absolute top-0 h-5 rounded bg-indigo-400" style={{ left: pos(a), width: `calc(${pos(b)} - ${pos(a)})` }} />
                <span className="absolute -top-0.5 h-6 w-0.5 bg-amber-500" style={{ left: pos(data.current_kw) }} title="Current what-if" />
              </div>
              <div className="mt-0.5 flex justify-between text-xs text-slate-400">
                <span>{featureValueText(r.feature, r.low)} → {fmtKw(r.at_low_kw)}</span><span>{featureValueText(r.feature, r.high)} → {fmtKw(r.at_high_kw)}</span>
              </div>
            </li>
          );
        })}
      </ul>
      <p className="mt-3 text-xs text-slate-400"><span className="inline-block h-2 w-0.5 bg-amber-500 align-middle" /> orange tick = demand in your current what-if. Scale: {lo} to {hi} kW.</p>
    </Card>
  );
}
