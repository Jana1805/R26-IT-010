import React from 'react';
import { ComposedChart, Area, Line, XAxis, YAxis, Tooltip, ReferenceLine, ResponsiveContainer, CartesianGrid, Legend } from 'recharts';
import { Card } from './Card.jsx';
import { fmtHour, fmtKw } from '../lib/labels.js';

const SNAP_COLORS = ['#0d9488', '#c026d3'];

export default function DemandChart({ curve, hour, capacity, snapshots, showCapacity = true }) {
  const data = curve.hours.map((h, i) => {
    const row = { hour: h, normal: curve.baseline[i], whatif: curve.scenario[i] };
    snapshots.forEach((s, j) => { row[`snap${j}`] = s.curve[i]; });
    return row;
  });
  const maxY = Math.max(capacity * 1.05, ...data.map((d) => Math.max(d.normal, d.whatif)));
  return (
    <Card id="chart-card" className="!p-4 sm:!p-5">
      <h3 className="mb-1 text-base font-semibold text-slate-900">How demand moves through the day</h3>
      <p className="mb-3 text-sm text-slate-500">The blue area is your what-if. The dashed grey line is a normal day. Anything above the red line is more than the grid can supply.</p>
      <div style={{ width: '100%', height: 340 }}>
        <ResponsiveContainer>
          <ComposedChart data={data} margin={{ top: 24, right: 16, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="whatifFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.35} /><stop offset="95%" stopColor="#4f46e5" stopOpacity={0.03} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="hour" tickFormatter={(h) => (h % 3 === 0 ? fmtHour(h) : '')} interval={0} tick={{ fontSize: 12 }} />
            <YAxis domain={[0, Math.ceil(maxY / 100) * 100]} tick={{ fontSize: 12 }} width={56} tickFormatter={(v) => `${v}`} label={{ value: 'kW', angle: -90, position: 'insideLeft', fontSize: 12 }} />
            <Tooltip formatter={(v, n) => [fmtKw(v), n]} labelFormatter={(h) => fmtHour(h)} />
            <Legend verticalAlign="bottom" height={28} wrapperStyle={{ fontSize: 12 }} />
            <Area type="monotone" dataKey="whatif" name="Your what-if" stroke="#4f46e5" strokeWidth={2.5} fill="url(#whatifFill)" isAnimationActive={false} />
            <Line type="monotone" dataKey="normal" name="Normal day" stroke="#64748b" strokeDasharray="6 4" strokeWidth={2} dot={false} isAnimationActive={false} />
            {snapshots.map((s, j) => (
              <Line key={s.id} type="monotone" dataKey={`snap${j}`} name={`Saved: ${s.name}`} stroke={SNAP_COLORS[j % 2]} strokeWidth={2} dot={false} isAnimationActive={false} />
            ))}
            {showCapacity && <ReferenceLine y={capacity} stroke="#dc2626" strokeWidth={2} label={{ value: `Supply limit ${capacity} kW`, fill: '#dc2626', fontSize: 12, position: 'insideTopRight' }} />}
            <ReferenceLine x={hour} stroke="#f59e0b" strokeWidth={2} label={{ value: fmtHour(hour), fill: '#b45309', fontSize: 12, position: 'top' }} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
