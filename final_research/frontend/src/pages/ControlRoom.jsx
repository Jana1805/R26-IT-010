import React, { useEffect, useMemo, useRef, useState } from 'react';
import { getReference, getCurve, getExplain, getSensitivity } from '../lib/api.js';
import { describeChanges, fmtHour, gridStatus, headline, recommendations } from '../lib/labels.js';
import { exportScenarioPdf } from '../lib/exportPdf.js';
import PickDay, { DAY_TYPES, WEATHER_PRESETS } from '../components/PickDay.jsx';
import WhatIf from '../components/WhatIf.jsx';
import DemandChart from '../components/DemandChart.jsx';
import ImpactCard from '../components/ImpactCard.jsx';
import StatusGauge from '../components/StatusGauge.jsx';
import Recommendations from '../components/Recommendations.jsx';
import DriverBars from '../components/DriverBars.jsx';
import Tornado from '../components/Tornado.jsx';
import Compare from '../components/Compare.jsx';
import Tour from '../components/Tour.jsx';

const toBaselineApi = (b) => ({
  'Temperature (°C)': b.temp, 'Humidity (%)': b.humidity, 'Electricity Price (LKR/kWh)': b.price, 'GDP (LKR)': b.gdp,
  Month: b.month, 'Day of Week': b.dow, 'Poya Day': b.poya, 'Public Event': b.event,
});
const toScenarioApi = (s) => ({
  'Temperature (°C)': s.temp, 'Humidity (%)': s.humidity, 'Electricity Price (LKR/kWh)': s.price, 'GDP (LKR)': s.gdp,
});

export default function ControlRoom() {
  const [ref, setRef] = useState(null);
  const [error, setError] = useState(null);
  const [base, setBase] = useState(null);
  const [scen, setScen] = useState(null);
  const [dayType, setDayType] = useState('weekday');
  const [weather, setWeather] = useState('typical');
  const [preset, setPreset] = useState(null);
  const [capacity, setCapacity] = useState(2200);
  const [curve, setCurve] = useState(null);
  const [explain, setExplain] = useState(null);
  const [sens, setSens] = useState(null);
  const [snapshots, setSnapshots] = useState([]);
  const [tour, setTour] = useState(null);
  const [exporting, setExporting] = useState(false);
  const req = useRef(0);

  useEffect(() => {
    getReference().then((r) => {
      const t = r.typical;
      const b = { temp: 28, humidity: 80, price: Math.round(t['Electricity Price (LKR/kWh)']), gdp: Math.round(t['GDP (LKR)']), month: 6, dow: 2, hour: 19, poya: 0, event: 0 };
      setRef(r); setBase(b); setScen({ temp: b.temp, humidity: b.humidity, price: b.price, gdp: b.gdp });
      setCapacity(r.default_capacity_kw);
    }).catch((e) => setError(e.message));
  }, []);

  // Debounced refresh of curve, explanation and sensitivity whenever inputs change.
  useEffect(() => {
    if (!base || !scen) return;
    const id = ++req.current;
    const t = setTimeout(async () => {
      try {
        const bApi = toBaselineApi(base), sApi = toScenarioApi(scen);
        const [c, e, s] = await Promise.all([
          getCurve(bApi, sApi), getExplain(bApi, sApi, base.hour), getSensitivity({ ...bApi, ...sApi }, base.hour),
        ]);
        if (id === req.current) { setCurve(c); setExplain(e); setSens(s); setError(null); }
      } catch (err) { if (id === req.current) setError(err.message); }
    }, 150);
    return () => clearTimeout(t);
  }, [base, scen]);

  const derived = useMemo(() => {
    if (!curve || !base) return null;
    const baseKw = curve.baseline[base.hour], scenKw = curve.scenario[base.hour];
    const head = headline({ base, scen, hour: base.hour, baseKw, scenKw });
    const peakKw = curve.scenario_stats.peak, peakHour = curve.scenario_stats.peak_hour;
    const status = gridStatus(peakKw, capacity);
    const recs = recommendations({ status, peakKw, capacityKw: capacity, capacity, peakHour, explain, base, scen });
    return { baseKw, scenKw, head, peakKw, peakHour, status, recs, changes: describeChanges(base, scen) };
  }, [curve, base, scen, capacity, explain]);

  if (error && !ref) return <Shell><p className="rounded-xl bg-rose-50 p-4 text-rose-700">Could not reach the forecasting service: {error}</p></Shell>;
  if (!ref || !base || !scen) return <Shell><p className="text-slate-500">Loading the control room…</p></Shell>;

  const resetScenario = (b = base) => { setScen({ temp: b.temp, humidity: b.humidity, price: b.price, gdp: b.gdp }); setPreset(null); };
  const onDayType = (d) => { setDayType(d.key); setBase((b) => ({ ...b, ...d.set })); };
  const onWeather = (w) => {
    setWeather(w.key);
    const nb = { ...base, temp: w.temp, humidity: w.humidity };
    setBase(nb); resetScenario(nb);
  };
  const onPreset = (p) => {
    const next = p.apply({ temp: base.temp, humidity: base.humidity, price: base.price, gdp: base.gdp });
    setScen({ temp: next.temp, humidity: next.humidity, price: next.price, gdp: next.gdp }); setPreset(p.key);
  };
  const onSlider = (patch) => { setScen((s) => ({ ...s, ...patch })); setPreset(null); };
  const dirty = derived && derived.changes;

  const saveSnapshot = () => {
    if (!derived || !dirty || snapshots.length >= 2) return;
    const name = snapshots.some((s) => s.name === 'Scenario A') ? 'Scenario B' : 'Scenario A';
    setSnapshots((prev) => [...prev, {
      id: Date.now(), name, curve: curve.scenario, changes: derived.changes,
      peak: derived.peakKw, peakHour: derived.peakHour, diff: derived.head.diff,
    }]);
  };

  const doExport = async () => {
    setExporting(true);
    try {
      await exportScenarioPdf({ base, scen, head: derived.head, status: derived.status, capacity, peakKw: derived.peakKw,
        peakHour: derived.peakHour, hour: base.hour, recs: derived.recs, explain, ref, changes: derived.changes });
    } finally { setExporting(false); }
  };

  const perf = ref.performance || {};
  return (
    <Shell
      actions={(
        <div className="flex flex-wrap gap-2">
          <button onClick={() => setTour(0)} className="rounded-lg border border-indigo-300 bg-white px-4 py-2 text-sm font-semibold text-indigo-700 hover:bg-indigo-50">▶ Guided tour</button>
          <button id="export-btn" onClick={doExport} disabled={!derived || exporting}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">
            {exporting ? 'Building PDF…' : '⬇ Export PDF'}
          </button>
        </div>
      )}
      perf={perf}
    >
      {error && <p className="rounded-xl bg-amber-50 p-3 text-sm text-amber-800">Connection hiccup: {error}</p>}
      <PickDay base={base} dayType={dayType} weather={weather} onDayType={onDayType} onWeather={onWeather}
        onMonth={(m) => setBase((b) => ({ ...b, month: m }))} onHour={(h) => setBase((b) => ({ ...b, hour: h }))} />
      <WhatIf base={base} scen={scen} ranges={ref.ranges} onChange={onSlider} onPreset={onPreset} onReset={() => resetScenario()} activePreset={preset} />
      {derived && curve ? (
        <>
          <ImpactCard head={derived.head} scenKw={derived.scenKw} baseKw={derived.baseKw} />
          <DemandChart curve={curve} hour={base.hour} capacity={capacity} snapshots={snapshots} />
          <StatusGauge peakKw={derived.peakKw} peakHour={derived.peakHour} capacity={capacity} onCapacity={setCapacity}
            status={derived.status} min={1200} max={3500} />
          <div className="grid gap-5 lg:grid-cols-2">
            <DriverBars explain={explain} />
            <Recommendations recs={derived.recs} />
          </div>
          <div className="grid gap-5 lg:grid-cols-2">
            <Tornado data={sens} />
            <Compare snapshots={snapshots} canSave={!!dirty && snapshots.length < 2} onSave={saveSnapshot}
              onRemove={(id) => setSnapshots((p) => p.filter((s) => s.id !== id))} />
          </div>
        </>
      ) : <p className="text-slate-500">Calculating…</p>}
      {tour !== null && <Tour step={tour} onStep={setTour} onClose={() => setTour(null)} />}
    </Shell>
  );
}

function Shell({ children, actions, perf }) {
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-5 sm:px-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Electricity Demand Control Room</h1>
            <p className="max-w-2xl text-sm text-slate-500">
              See how weather, prices and the economy change how much power Sri Lanka needs, and whether the grid can keep up. Follow the three steps below.
            </p>
          </div>
          {actions}
        </div>
        {perf && (
          <div className="mx-auto max-w-6xl px-4 pb-3 text-xs text-slate-500 sm:px-6">
            Forecast model accuracy: <b>{(perf.test_r2 * 100).toFixed(0)}%</b> of the variation explained (R² {perf.test_r2?.toFixed(2)}), typical error about <b>{Math.round(perf.test_mae)} kW</b>. Synthetic practice data.
          </div>
        )}
      </header>
      <main className="mx-auto flex max-w-6xl flex-col gap-5 px-4 py-6 sm:px-6">{children}</main>
      <footer className="mx-auto max-w-6xl px-4 pb-10 text-xs text-slate-400 sm:px-6">
        Effects are model estimates from one-factor-at-a-time what-ifs. Training data is synthetic (see backup_original_dataset/README.md).
      </footer>
    </div>
  );
}
