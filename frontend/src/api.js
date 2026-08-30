// src/api.js — all API calls in one place
// Use Vite proxy by default to avoid CORS/host issues in local dev.
const BASE = import.meta.env.VITE_API_BASE_URL || "/api";
const FORECAST_PASSES = Number(import.meta.env.VITE_FORECAST_PASSES || 5);
const FORECAST_STEPS = Number(import.meta.env.VITE_FORECAST_STEPS || 24);
// Increase default timeout to 180s to accommodate longer model inference
const REQUEST_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS || 180000);

const get = async (path) => {
  const ctrl = new AbortController();
  const timeoutId = setTimeout(() => ctrl.abort(), REQUEST_TIMEOUT_MS);
  let res;
  try {
    res = await fetch(`${BASE}${path}`, { signal: ctrl.signal });
  } catch (err) {
    if (err.name === "AbortError") {
      throw new Error(`Request timeout after ${Math.round(REQUEST_TIMEOUT_MS / 1000)}s`);
    }
    throw new Error(`Failed to reach backend: ${err.message}`);
  } finally {
    clearTimeout(timeoutId);
  }

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API error ${res.status}${body ? `: ${body}` : ""}`);
  }

  return res.json();
};

export const api = {
  health:      ()                => get("/health"),
  dataSource:  ()                => get("/data/source"),
  dataRange:   ()                => get("/data/range"),
  liveDemand:  ()                => get("/demand/live"),
  historical:  (hours = 24, endTimestamp = null) =>
    get(`/demand/historical?hours=${hours}${endTimestamp ? `&end_timestamp=${encodeURIComponent(endTimestamp)}` : ""}`),
  forecast:    ({ steps = FORECAST_STEPS, startTimestamp = null, includeActuals = true, model = null } = {}) =>
    get(
      `/forecast?steps=${steps}&n_passes=${FORECAST_PASSES}` +
      `${startTimestamp ? `&start_timestamp=${encodeURIComponent(startTimestamp)}` : ""}` +
      `&include_actuals=${includeActuals ? 1 : 0}` +
      `${model ? `&model=${encodeURIComponent(model)}` : ""}`
    ),
  heatmap:     ()                => get("/analysis/heatmap"),
  metrics:     (model = null)    => get(`/model/metrics${model ? `?model=${encodeURIComponent(model)}` : ""}`),
  models:      ()                => get("/models"),
  registry:    ()                => get("/api/models"),
  comparison:  ()                => get("/api/comparison?sample_limit=600"),
};
