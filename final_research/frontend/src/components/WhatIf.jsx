import React from 'react';
import { Card, Chip } from './Card.jsx';
import { SCENARIO_PRESETS } from '../lib/labels.js';

function Slider({ label, hint, min, max, step, value, baseValue, display, baseDisplay, onChange }) {
  const changed = Math.abs(value - baseValue) > step / 2;
  const pctBase = ((baseValue - min) / (max - min)) * 100;
  return (
    <div className="rounded-xl bg-slate-50 p-4">
      <div className="flex items-baseline justify-between">
        <span className="text-sm font-semibold text-slate-800">{label}</span>
        <span className={`text-sm font-bold ${changed ? 'text-indigo-700' : 'text-slate-500'}`}>{display}</span>
      </div>
      <div className="relative mt-3">
        <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))}
          className="relative z-10 h-2 w-full cursor-pointer accent-indigo-600" aria-label={label} />
        <span className="pointer-events-none absolute -bottom-3 h-2 w-0.5 bg-slate-400" style={{ left: `calc(${pctBase}% )` }} />
      </div>
      <p className="mt-4 text-xs text-slate-500">{hint} <span className="text-slate-400">Normal: {baseDisplay}</span></p>
    </div>
  );
}

export default function WhatIf({ base, scen, ranges, onChange, onPreset, onReset, activePreset }) {
  const r = ranges;
  return (
    <Card id="step2" step="2" title="Ask a 'what if…'"
      subtitle="Drag a slider, or tap a quick scenario. The chart below redraws instantly.">
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <span className="text-sm text-slate-500">Quick scenarios:</span>
        {SCENARIO_PRESETS.map((p) => (
          <Chip key={p.key} active={activePreset === p.key} title={p.blurb} onClick={() => onPreset(p)}>{p.emoji} {p.label}</Chip>
        ))}
        <button onClick={onReset} className="ml-auto text-sm text-indigo-700 underline-offset-2 hover:underline">Reset to normal</button>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Slider label="🌡️ Temperature" hint="Hotter days mean more air-conditioning." min={15} max={42} step={0.5}
          value={scen.temp} baseValue={base.temp} display={`${scen.temp.toFixed(1)} °C`} baseDisplay={`${base.temp.toFixed(1)} °C`}
          onChange={(v) => onChange({ temp: v })} />
        <Slider label="💧 Humidity" hint="Muggy air makes cooling work harder." min={30} max={100} step={1}
          value={scen.humidity} baseValue={base.humidity} display={`${Math.round(scen.humidity)} %`} baseDisplay={`${Math.round(base.humidity)} %`}
          onChange={(v) => onChange({ humidity: v })} />
        <Slider label="💸 Electricity price" hint="When power costs more, people use less." min={Math.round(r['Electricity Price (LKR/kWh)'].min)} max={Math.round(r['Electricity Price (LKR/kWh)'].max) + 20} step={0.5}
          value={scen.price} baseValue={base.price} display={`${scen.price.toFixed(1)} LKR/kWh`} baseDisplay={`${base.price.toFixed(1)} LKR/kWh`}
          onChange={(v) => onChange({ price: v })} />
        <Slider label="📈 Economic activity" hint="A bigger economy uses more power." min={Math.round(base.gdp * 0.7)} max={Math.round(base.gdp * 1.4)} step={5}
          value={scen.gdp} baseValue={base.gdp} display={`${scen.gdp >= base.gdp ? '+' : '−'}${Math.abs((scen.gdp / base.gdp - 1) * 100).toFixed(0)} % vs normal`} baseDisplay="no change"
          onChange={(v) => onChange({ gdp: v })} />
      </div>
    </Card>
  );
}
