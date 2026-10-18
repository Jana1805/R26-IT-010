export function formatKW(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) return value ?? '—';
  return Math.round(value).toLocaleString('en-US');
}

export function formatScore(value, dp = 4) {
  if (typeof value !== 'number' || Number.isNaN(value)) return value ?? '—';
  return value.toFixed(dp);
}

export function formatPercent(value, dp = 2) {
  if (typeof value !== 'number' || Number.isNaN(value)) return value ?? '—';
  return `${value.toFixed(dp)}%`;
}
