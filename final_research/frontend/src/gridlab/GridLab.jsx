import React, { useEffect, useState } from 'react';
import axios from 'axios';
import SriLankaMap from './SriLankaMap.jsx';
import { BarChart, Bar, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { LEVELS, levelOf, pct } from './risk.js';

const fmtHour = (h) => `${h % 12 === 0 ? 12 : h % 12} ${h < 12 ? 'AM' : 'PM'}`;
const SUPPLY_LIMIT_KW = 2300;
const card = 'rounded-lg bg-white p-5 shadow';
const DAY_TYPES = [
  { key: 'today', label: 'Today' }, { key: 'weekday', label: 'Weekday', dow: 2 },
  { key: 'weekend', label: 'Weekend', dow: 5 }, { key: 'poya', label: 'Poya holiday', dow: 2, poya: 1 },
];
const WEATHER = [
  { key: 'live', label: 'Real weather now' }, { key: 'normal', label: 'Normal', temp: 28, humidity: 80 },
  { key: 'hot', label: 'Hot', temp: 33, humidity: 80 }, { key: 'heat', label: 'Heat wave', temp: 37, humidity: 75 },
];
const hourRange = (hs) => (hs.length === 1 ? fmtHour(hs[0]) : `${fmtHour(hs[0])} to ${fmtHour(hs[hs.length - 1] + 1)}`);

function Pills({ options, value, onChange }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((o) => (
        <button key={o.key} onClick={() => onChange(o.key)}
          className={`rounded-full border px-3 py-1 text-sm ${value === o.key ? 'border-blue-600 bg-blue-600 text-white' : 'border-gray-300 bg-white text-gray-700 hover:border-blue-400'}`}>{o.label}</button>
      ))}
    </div>
  );
}

export default function GridLab() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [hour, setHour] = useState(19);
  const [playing, setPlaying] = useState(false);
  const [started, setStarted] = useState(false);

  const [dayType, setDayType] = useState('today');
  const [weather, setWeather] = useState('live');

  useEffect(() => {
    const d = DAY_TYPES.find((x) => x.key === dayType), w = WEATHER.find((x) => x.key === weather);
    const calendar = { dow_override: d.dow ?? null, dow: d.dow ?? 2, poya: d.poya || 0 };
    const req = w.key === 'live'
      ? { source: 'live', capacity: SUPPLY_LIMIT_KW, ...calendar }
      : { source: 'scenario', temp: w.temp, humidity: w.humidity, capacity: SUPPLY_LIMIT_KW, ...calendar };
    let alive = true; setError(null);
    axios.post('/api/decision', req)
      .catch(() => {
        if (req.source !== 'live') throw new Error('The forecasting service did not respond.');
        setError('Live weather could not be reached, so a normal 28 °C day is shown instead.');
        return axios.post('/api/decision', { ...req, source: 'scenario', temp: 28, humidity: 80 });
      })
      .then((r) => {
        if (!alive) return;
        setData(r.data);
        if (!started && r.data.live) { setHour(Number(r.data.live.time.slice(11, 13))); setStarted(true); }
      })
      .catch((e) => alive && setError(e.response?.data?.detail || e.message));
    return () => { alive = false; };
  }, [dayType, weather]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!playing) return undefined;
    const t = setInterval(() => setHour((h) => (h + 1) % 24), 700);
    return () => clearInterval(t);
  }, [playing]);

  const nat = data?.national;
  const worst = nat && levelOf(nat.worst_p);
  const day = data?.live ? new Date(`${data.live.time.slice(0, 10)}T12:00:00`) : new Date();
  const realDay = day.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  const dayText = dayType === 'today' ? realDay : { weekday: 'A typical weekday', weekend: 'A typical weekend day', poya: 'A Poya holiday' }[dayType];
  const caption = weather === 'live' && data?.live ? (dayType === 'today' ? 'Today (live weather)' : 'Real weather now') : (dayType === 'today' ? 'Sample day' : 'Chosen day');
  const maxD = nat ? Math.max(...nat.demand) : 0;
  const busy = nat ? nat.demand.map((d, h) => (d >= maxD * 0.95 ? h : -1)).filter((h) => h >= 0) : [];
  const strip = nat ? nat.demand.map((d, h) => ({ hour: h, demand: Math.round(d), busy: busy.includes(h) })) : [];
  const atHour = nat ? levelOf(nat.p[hour]) : null;
  const peakHour = nat ? nat.demand.indexOf(Math.max(...nat.demand)) : 0;

  return (
    <div className="space-y-6">
      {error && <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">{error}</p>}

      {/* Filters */}
      <div className={`${card} flex flex-wrap items-start gap-x-8 gap-y-3`}>
        <div><p className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">Day</p><Pills options={DAY_TYPES} value={dayType} onChange={setDayType} /></div>
        <div><p className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">Weather</p><Pills options={WEATHER} value={weather} onChange={setWeather} /></div>
      </div>

      {/* Day + time of day */}
      <div className={`${card} flex flex-wrap items-center justify-between gap-4`}>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">{caption}</p>
          <p className="text-2xl font-bold text-gray-900">{dayText}</p>
        </div>
        <div className="min-w-[16rem] flex-1 sm:max-w-md">
          <p className="mb-1 text-sm font-semibold text-gray-900">Time of day: {fmtHour(hour)}</p>
          <div className="flex items-center gap-2">
            <button onClick={() => setPlaying((p) => !p)} className="rounded-full bg-gray-900 px-3 py-1 text-xs font-semibold text-white">{playing ? '❚❚ Pause' : '▶ Play day'}</button>
            <input type="range" min={0} max={23} value={hour} onChange={(e) => { setHour(Number(e.target.value)); setPlaying(false); }} className="flex-1 accent-gray-900" aria-label="Hour of day" />
          </div>
        </div>
      </div>

      {/* When does demand climb? */}
      {nat && (
        <div className={card}>
          <p className="text-sm font-semibold text-gray-900">When does demand climb?</p>
          <p className="text-sm text-gray-600">Demand is highest around <b>{hourRange(busy)}</b>. Orange bars are the busiest hours; click a bar to look at that hour on the map.</p>
          <div style={{ height: 110 }} className="mt-2">
            <ResponsiveContainer>
              <BarChart data={strip} margin={{ top: 4, right: 4, bottom: 0, left: 0 }} onClick={(e) => e?.activeLabel !== undefined && (setHour(Number(e.activeLabel)), setPlaying(false))}>
                <XAxis dataKey="hour" tickFormatter={(h) => (h % 3 === 0 ? fmtHour(h) : '')} interval={0} tick={{ fontSize: 10 }} />
                <YAxis hide domain={[0, 'dataMax']} />
                <Tooltip formatter={(v) => [`${v} kW`, 'Demand']} labelFormatter={fmtHour} />
                <Bar dataKey="demand" isAnimationActive={false} cursor="pointer">
                  {strip.map((r) => <Cell key={r.hour} fill={r.busy ? '#f97316' : r.hour === hour ? '#1d4ed8' : '#93c5fd'} stroke={r.hour === hour ? '#1e3a8a' : 'none'} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Whole country */}
      {nat && worst && (
        <div className="rounded-lg p-5 shadow" style={{ background: worst.soft }}>
          <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: worst.color }}>Whole country</p>
          <p className="mt-1 text-xl font-semibold text-gray-900">
            {nat.worst_p < 0.03
              ? <>No hour of this day is likely to run short. The busiest hour is <b>{fmtHour(peakHour)}</b> at {Math.round(nat.demand[peakHour])} kW (<b style={{ color: worst.color }}>{pct(nat.p[peakHour])}</b> overload chance).</>
              : <>Worst hour of the day is <b>{fmtHour(nat.worst_hour)}</b>: <b style={{ color: worst.color }}>{pct(nat.worst_p)}</b> chance demand passes supply ({worst.label.toLowerCase()}).</>}
          </p>
          <p className="mt-1 text-sm text-gray-700">
            At {fmtHour(hour)}: demand {Math.round(nat.demand[hour])} kW of {Math.round(nat.capacity)} kW supply, overload chance <b style={{ color: atHour.color }}>{pct(nat.p[hour])}</b>.
          </p>
        </div>
      )}

      {/* Map */}
      <div className={card}>
        {data ? (
          <>
            <SriLankaMap regions={data.regions} hour={hour} selected={null} onSelect={() => {}} />
            <div className="mt-3 flex flex-wrap justify-center gap-3 text-xs text-gray-600">
              {LEVELS.map((l) => <span key={l.key} className="flex items-center gap-1"><i className="inline-block h-3 w-3 rounded-sm" style={{ background: l.color }} />{l.label}</span>)}
            </div>
            <p className="mt-2 text-center text-xs text-gray-500">Hover a province for its temperature, demand and overload chance at {fmtHour(hour)}.</p>
          </>
        ) : <p className="text-sm text-gray-500">Loading map…</p>}
      </div>

      {/* How this works */}
      <div className={card}>
        <h4 className="mb-2 font-semibold text-gray-900">How this works</h4>
        <ol className="list-decimal space-y-1.5 pl-5 text-sm text-gray-700">
          <li><b>Weather in.</b> We read today's real temperature and humidity for each province capital (Open-Meteo), hour by hour.</li>
          <li><b>Demand out.</b> The trained forecasting model turns that weather, the time of day and the calendar into expected electricity demand for each province.</li>
          <li><b>Risk.</b> No forecast is exact. Using how wrong the model was on data it had never seen, we work out the chance that real demand ends up higher than the supply available. That chance is the colour.</li>
          <li><b>Map.</b> Green means safe, yellow watch, orange at risk, red likely overload. Drag the time slider or press Play day to see the pressure move through the day.</li>
        </ol>
        <p className="mt-3 rounded-lg bg-gray-50 p-3 text-xs text-gray-600">
          <b>What is real and what is assumed:</b> province shapes and live weather are real. Demand is modelled from synthetic practice data, not meter readings.
          Each province's share of national demand and its spare capacity are illustrative assumptions, and the national supply limit is set to {SUPPLY_LIMIT_KW} kW, because the dataset has no regional information.
        </p>
      </div>
    </div>
  );
}
