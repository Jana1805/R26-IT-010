import React, { useEffect, useState } from 'react';
import axios from 'axios';

const card = 'rounded-lg border border-gray-200 bg-white p-4';

export default function PerformancePanel() {
  const [d, setD] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => { axios.get('/api/performance').then((r) => setD(r.data)).catch((e) => setErr(e.response?.data?.detail || e.message)); }, []);
  if (err) return <p className="text-sm text-red-600">Could not load performance data: {err}</p>;
  if (!d) return <p className="text-sm text-gray-500">Loading…</p>;
  const m = d.metrics;
  const names = Object.keys(d.comparison);
  // The deployed model is the one whose test R² matches the headline metrics (it is not always the highest R² row: the tuned model is chosen by cross-validation).
  const deployed = names.find((n) => Math.abs(d.comparison[n].test_r2 - m.test_r2) < 1e-9);
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className={card}>
        <h4 className="font-semibold text-gray-900">Train vs test</h4>
        <table className="mt-2 w-full text-sm">
          <thead><tr className="text-left text-xs uppercase text-gray-400"><th /><th>R²</th><th>MAE (kW)</th><th>RMSE (kW)</th></tr></thead>
          <tbody>
            <tr className="border-t"><td className="py-1.5">Train</td><td>{m.train_r2.toFixed(3)}</td><td>{m.train_mae.toFixed(1)}</td><td>{m.train_rmse.toFixed(1)}</td></tr>
            <tr className="border-t"><td className="py-1.5">Test</td><td>{m.test_r2.toFixed(3)}</td><td>{m.test_mae.toFixed(1)}</td><td>{m.test_rmse.toFixed(1)}</td></tr>
          </tbody>
        </table>
        <p className="mt-2 text-xs text-gray-500">Nearly identical scores mean the model is not just memorising the training data.</p>
      </div>
      <div className={card}>
        <h4 className="font-semibold text-gray-900">Model comparison</h4>
        <table className="mt-2 w-full text-sm">
          <thead><tr className="text-left text-xs uppercase text-gray-400"><th>Model</th><th>R²</th><th>MAE (kW)</th><th>RMSE (kW)</th></tr></thead>
          <tbody>
            {names.map((n) => (
              <tr key={n} className={`border-t ${n === deployed ? 'bg-emerald-50 font-semibold' : ''}`}>
                <td className="py-1.5">{n} {n === deployed && '✅ deployed'}</td><td>{d.comparison[n].test_r2.toFixed(3)}</td><td>{d.comparison[n].test_mae.toFixed(1)}</td><td>{d.comparison[n].test_rmse.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
