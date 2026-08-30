import { ACTUAL_SERIES, EMPTY_VALUE, formatDemandDetail, formatTimestamp, MODEL_SERIES } from "../dashboardData";

const points = {
  circle: <circle cx="15" cy="6" r="3" />,
  square: <rect x="12" y="3" width="6" height="6" />,
  triangle: <path d="M15 2 19 9H11Z" />,
  triangleDown: <path d="M11 3h8l-4 7Z" />,
  diamond: <path d="m15 1 5 5-5 5-5-5Z" />,
  cross: <path d="M13 1h4v3h3v4h-3v3h-4V8h-3V4h3Z" />,
  hexagon: <path d="m12 2 6 0 3 4-3 4h-6L9 6Z" />,
};

export function SeriesSwatch({ modelId, actual = false }) {
  const series = actual ? ACTUAL_SERIES : MODEL_SERIES[modelId];
  if (!series) return null;
  return <span className="series-swatch" aria-hidden="true"><svg width="30" height="12" viewBox="0 0 30 12"><line x1="1" x2="29" y1="6" y2="6" stroke={series.color} strokeWidth={actual ? 2.75 : 2} strokeDasharray={series.dash}/><g fill={series.color}>{points[series.marker]}</g></svg></span>;
}

export function ModelLegendLabel({ modelId, label }) {
  const series = MODEL_SERIES[modelId];
  return <span className="model-name"><SeriesSwatch modelId={modelId}/><span>{label ?? series?.shortLabel ?? modelId}</span></span>;
}

export function DemandTooltip({ active, payload, label, forecastMeta }) {
  if (!active || !payload?.length) return null;
  const timestamp=payload[0]?.payload?.timestamp??label;
  return <div className="chart-tooltip" role="status"><strong>{formatTimestamp(timestamp)}</strong>{payload.map(item => {
    if (item.value == null) return null;
    const value=Array.isArray(item.value)?`${formatDemandDetail(item.value[0])}–${formatDemandDetail(item.value[1])}`:formatDemandDetail(item.value);
    return <div className="chart-tooltip__row" key={item.dataKey}><span className="chart-tooltip__key"><span style={{background:item.color}}/>{item.name}</span><strong>{value}</strong></div>;
  })}{forecastMeta?.interval_note&&<small>{forecastMeta.interval_note}</small>}</div>;
}

export function ChartDescription({ id, children }) {
  return <p id={id} className="sr-only">{children || EMPTY_VALUE}</p>;
}

export function CsvDownload({ rows=[], columns, filename, children="Download chart data" }) {
  const download=()=>{
    const keys=columns??Object.keys(rows[0]??{});
    const escape=value=>`"${String(value??"").replaceAll('"','""')}"`;
    const csv=[keys,...rows.map(row=>keys.map(key=>row[key]))].map(row=>row.map(escape).join(",")).join("\n");
    const url=URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8"}));
    const anchor=document.createElement("a");anchor.href=url;anchor.download=filename;anchor.click();URL.revokeObjectURL(url);
  };
  return <button type="button" className="button button--quiet chart-data-action" onClick={download} disabled={!rows.length}>{children}</button>;
}
