import React from 'react';
import { Card } from './Card.jsx';
import { describeChanges, fmtHour, fmtKw, fmtSigned } from '../lib/labels.js';

export default function Compare({ snapshots, canSave, onSave, onRemove }) {
  return (
    <Card id="compare-card" title="Compare scenarios" subtitle="Save up to two what-ifs and see them side by side on the chart.">
      <button disabled={!canSave} onClick={onSave}
        className="mb-3 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40">
        Save current what-if
      </button>
      {snapshots.length === 0 ? <p className="text-sm text-slate-500">Nothing saved yet.</p> : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead><tr className="text-xs uppercase text-slate-400"><th className="py-1 pr-3">Scenario</th><th className="pr-3">What changed</th><th className="pr-3">Peak</th><th className="pr-3">vs normal</th><th /></tr></thead>
            <tbody>
              {snapshots.map((s, i) => (
                <tr key={s.id} className="border-t border-slate-100">
                  <td className="py-2 pr-3 font-semibold" style={{ color: ['#0d9488', '#c026d3'][i % 2] }}>{s.name}</td>
                  <td className="pr-3 text-slate-600">{s.changes || 'no change'}</td>
                  <td className="pr-3">{fmtKw(s.peak)} at {fmtHour(s.peakHour)}</td>
                  <td className="pr-3 font-semibold">{fmtSigned(s.diff)} kW</td>
                  <td><button onClick={() => onRemove(s.id)} className="text-xs text-slate-400 hover:text-rose-600">remove</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
