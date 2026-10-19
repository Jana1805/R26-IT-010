import React from 'react';
import { Card, Chip } from './Card.jsx';
import { MONTH_NAMES, fmtHour } from '../lib/labels.js';

export const WEATHER_PRESETS = [
  { key: 'typical', label: 'Typical', emoji: '🌤️', temp: 28, humidity: 80 },
  { key: 'hot', label: 'Hot and humid', emoji: '☀️', temp: 32, humidity: 88 },
  { key: 'cool', label: 'Cool and dry', emoji: '🌥️', temp: 24, humidity: 68 },
];
export const DAY_TYPES = [
  { key: 'weekday', label: 'Weekday', set: { dow: 2, poya: 0, event: 0 } },
  { key: 'weekend', label: 'Weekend', set: { dow: 5, poya: 0, event: 0 } },
  { key: 'poya', label: 'Poya holiday', set: { dow: 2, poya: 1, event: 0 } },
  { key: 'event', label: 'Public event', set: { dow: 2, poya: 0, event: 1 } },
];

export default function PickDay({ base, dayType, weather, onDayType, onWeather, onMonth, onHour }) {
  const sel = 'rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none';
  return (
    <Card id="step1" step="1" title="Pick a day"
      subtitle="Start from an ordinary day. This is the 'normal' we compare every what-if against.">
      <div className="grid gap-5 md:grid-cols-2">
        <div>
          <p className="mb-2 text-sm font-medium text-slate-700">What kind of day?</p>
          <div className="flex flex-wrap gap-2">
            {DAY_TYPES.map((d) => <Chip key={d.key} active={dayType === d.key} onClick={() => onDayType(d)}>{d.label}</Chip>)}
          </div>
          <p className="mb-2 mt-4 text-sm font-medium text-slate-700">What is the weather like?</p>
          <div className="flex flex-wrap gap-2">
            {WEATHER_PRESETS.map((w) => <Chip key={w.key} active={weather === w.key} onClick={() => onWeather(w)}>{w.emoji} {w.label}</Chip>)}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <label className="text-sm font-medium text-slate-700">Month
            <select className={`${sel} mt-1 block w-full`} value={base.month} onChange={(e) => onMonth(Number(e.target.value))}>
              {MONTH_NAMES.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
            </select>
          </label>
          <label className="text-sm font-medium text-slate-700">Hour to focus on
            <select className={`${sel} mt-1 block w-full`} value={base.hour} onChange={(e) => onHour(Number(e.target.value))}>
              {Array.from({ length: 24 }, (_, h) => <option key={h} value={h}>{fmtHour(h)}</option>)}
            </select>
          </label>
          <p className="col-span-2 text-xs text-slate-500">
            Demand follows a daily rhythm: low overnight, a small morning bump and a big evening peak. Pick the hour you care about and the numbers below will describe it.
          </p>
        </div>
      </div>
    </Card>
  );
}
