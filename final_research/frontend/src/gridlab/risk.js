// Shared risk colour/label rules (same thresholds as backend _status).
export const LEVELS = [
  { key: 'safe', min: 0, label: 'Safe', color: '#10b981', soft: '#d1fae5' },
  { key: 'watch', min: 0.03, label: 'Watch', color: '#eab308', soft: '#fef9c3' },
  { key: 'risk', min: 0.15, label: 'At risk', color: '#f97316', soft: '#ffedd5' },
  { key: 'overload', min: 0.5, label: 'Likely overload', color: '#dc2626', soft: '#fee2e2' },
];
export const levelOf = (p) => [...LEVELS].reverse().find((l) => p >= l.min) || LEVELS[0];
export const pct = (p) => (p < 0.001 ? '<0.1%' : p < 0.1 ? `${(p * 100).toFixed(1)}%` : `${Math.round(p * 100)}%`);
