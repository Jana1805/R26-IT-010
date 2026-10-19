import React, { useState } from 'react';
import { PROVINCES, MAP_SIZE } from '../data/provinces.js';
import { levelOf, pct } from './risk.js';

// Real province boundaries (geoBoundaries). Colour = chance that province's demand passes its capacity at the chosen hour.
export default function SriLankaMap({ regions, hour, selected, onSelect }) {
  const [hover, setHover] = useState(null);
  const byKey = Object.fromEntries(regions.map((r) => [r.key, r]));
  const h = hover && byKey[hover];
  return (
    <div className="relative mx-auto w-full max-w-[360px]">
      <svg viewBox={`0 0 ${MAP_SIZE.w} ${MAP_SIZE.h}`} className="w-full" role="img" aria-label="Sri Lanka provinces coloured by overload risk">
        {PROVINCES.map((p) => {
          const r = byKey[p.name]; if (!r) return null;
          const lvl = levelOf(r.p[hour]);
          const sel = selected === p.name;
          return (
            <g key={p.name} onMouseEnter={() => setHover(p.name)} onMouseLeave={() => setHover(null)} onClick={() => onSelect(p.name)} style={{ cursor: 'pointer' }}>
              <path d={p.d} fill={lvl.color} fillOpacity={sel ? 1 : 0.82} stroke={sel ? '#0f172a' : '#ffffff'} strokeWidth={sel ? 3 : 1.5} strokeLinejoin="round" />
              <text x={p.cx} y={p.cy - 2} textAnchor="middle" fontSize="10" fontWeight="700" fill="#0f172a" style={{ pointerEvents: 'none', paintOrder: 'stroke', stroke: '#fff', strokeWidth: 2.5 }}>{p.name.replace('North ', 'N. ')}</text>
              <text x={p.cx} y={p.cy + 10} textAnchor="middle" fontSize="10" fill="#0f172a" style={{ pointerEvents: 'none', paintOrder: 'stroke', stroke: '#fff', strokeWidth: 2.5 }}>{pct(r.p[hour])}</text>
            </g>
          );
        })}
      </svg>
      {h && (
        <div className="pointer-events-none absolute left-2 top-2 rounded-lg bg-slate-900/90 px-3 py-2 text-xs text-white shadow-lg">
          <p className="font-semibold">{h.key} ({h.city})</p>
          <p>Temp {h.temp[hour].toFixed(1)} °C</p>
          <p>Demand {Math.round(h.demand[hour])} / capacity {Math.round(h.capacity)} kW</p>
          <p>Overload chance {pct(h.p[hour])}</p>
        </div>
      )}
    </div>
  );
}
