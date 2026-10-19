import React from 'react';
import { Card } from './Card.jsx';

export default function Recommendations({ recs }) {
  return (
    <Card id="recs-card" title="What should we do?" subtitle="Suggested actions for this situation, written by simple rules, not by the model.">
      <ul className="space-y-3">
        {recs.map((r, i) => (
          <li key={i} className="flex gap-3 rounded-xl bg-slate-50 p-3">
            <span className="text-xl" aria-hidden>{r.icon}</span>
            <div><p className="font-semibold text-slate-900">{r.title}</p><p className="text-sm text-slate-600">{r.body}</p></div>
          </li>
        ))}
      </ul>
    </Card>
  );
}
