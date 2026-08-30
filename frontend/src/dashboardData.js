export const EMPTY_VALUE = "—";
export const MODEL_SERIES = {
  cnn: { shortLabel: "CNN", accessibleLabel: "Convolutional neural network forecast", color: "#0072B2", dash: undefined, marker: "circle" },
  lstm: { shortLabel: "LSTM", accessibleLabel: "Long short-term memory network forecast", color: "#D55E00", dash: "8 4", marker: "square" },
  transformer: { shortLabel: "Transformer", accessibleLabel: "Transformer network forecast", color: "#009E73", dash: "2 3", marker: "triangle" },
  cnn_lstm_b: { shortLabel: "CNN–LSTM-B", accessibleLabel: "CNN–LSTM baseline forecast", color: "#CC79A7", dash: "10 3 2 3", marker: "diamond" },
  cnn_transformer_b: { shortLabel: "CNN–Transformer-B", accessibleLabel: "CNN–Transformer baseline forecast", color: "#E69F00", dash: "12 4", marker: "triangleDown" },
  cnn_lstm_mc: { shortLabel: "CNN–LSTM MC", accessibleLabel: "CNN–LSTM forecast with Monte Carlo dropout", color: "#6F4E9C", dash: "5 3", marker: "cross" },
  cnn_transformer_mc: { shortLabel: "CNN–Transformer MC", accessibleLabel: "CNN–Transformer forecast with Monte Carlo dropout", color: "#8A5A2B", dash: "10 3 3 3 3 3", marker: "hexagon" },
};
export const MODEL_ORDER = Object.keys(MODEL_SERIES);
export const MODEL_COLORS = Object.fromEntries(Object.entries(MODEL_SERIES).map(([id, series]) => [id, series.color]));
export const ACTUAL_SERIES = { shortLabel: "Actual", accessibleLabel: "Observed electricity demand", color: "#17212B", marker: "circle" };

export const METRIC_INFO = {
  MAE: { label: "MAE", unit: "kW", help: "Average absolute difference between forecast and actual demand.", better: "lower" },
  RMSE: { label: "RMSE", unit: "kW", help: "Error measure that gives more weight to large misses.", better: "lower" },
  MAPE: { label: "MAPE", unit: "%", help: "Average forecast error as a percentage of actual demand.", better: "lower" },
  R2: { label: "R²", unit: "", help: "Share of demand variation explained by the model; closer to 1 is better.", better: "higher" },
};

const finite = value => value !== null && value !== undefined && Number.isFinite(Number(value));
const number = (value, digits) => Number(value).toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });

export const formatMetric = (metric, value) => {
  if (!finite(value)) return EMPTY_VALUE;
  const digits = metric === "R2" ? 4 : 2;
  const unit = METRIC_INFO[metric]?.unit;
  return `${Number(value).toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits })}${unit ? ` ${unit}` : ""}`;
};

export const formatDemand = value => finite(value) ? `${number(Math.round(Number(value)), 0)} kW` : EMPTY_VALUE;
export const formatDemandDetail = value => finite(value) ? `${number(value, 2)} kW` : EMPTY_VALUE;
export const formatInteger = value => finite(value) ? number(value, 0) : EMPTY_VALUE;
export const formatTimestamp = value => value ? new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Colombo" }).format(new Date(value)) : EMPTY_VALUE;
export const formatDate = value => value ? new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeZone: "Asia/Colombo" }).format(new Date(value)) : EMPTY_VALUE;
export const shortTime = value => value ? new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Asia/Colombo" }).format(new Date(value)) : EMPTY_VALUE;
export const compactDemandTick = value => finite(value) ? `${Math.round(Number(value) / 1000)}k` : EMPTY_VALUE;
export const toInputTimestamp = value => {
  if (!value) return ""; const date = new Date(value);
  const pad = part => String(part).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
};
export const modelFamily = id => id.includes("transformer") ? "Transformer" : id.includes("lstm") ? "Recurrent" : "Convolutional";
