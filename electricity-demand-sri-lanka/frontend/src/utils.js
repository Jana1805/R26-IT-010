// ── Number formatting ─────────────────────────────────────────────
export const fmt = (v) =>
  v?.toLocaleString("en-US", { maximumFractionDigits: 1 }) ?? "—";

// ── Timestamp → HH:MM ────────────────────────────────────────────
export const fmtTs = (ts) => {
  if (!ts) return "—";
  const d = new Date(ts);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
};

// ── Timestamp → datetime-local input value ────────────────────────
export const toInputTs = (ts) => {
  if (!ts) return "";
  const d = new Date(ts);
  return [
    d.getFullYear(),
    String(d.getMonth() + 1).padStart(2, "0"),
    String(d.getDate()).padStart(2, "0"),
  ].join("-") + "T" +
    String(d.getHours()).padStart(2, "0") + ":" +
    String(d.getMinutes()).padStart(2, "0");
};

// ── Heatmap cell colour ───────────────────────────────────────────
export const heatColor = (v, min, max) => {
  const t = (v - min) / (max - min || 1);
  if (t < 0.33) return `rgba(59,130,246,${0.2 + t * 0.8})`;
  if (t < 0.66) return `rgba(251,146,60,${0.3 + t * 0.6})`;
  return `rgba(239,68,68,${0.4 + t * 0.5})`;
};

// ── Days of week labels ───────────────────────────────────────────
export const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];