import { AlertCircle, CheckCircle2, HelpCircle, LoaderCircle, WifiOff } from "lucide-react";
import { EMPTY_VALUE, formatMetric, METRIC_INFO } from "../dashboardData";

export function MetricCard({ metric, value, label, detail }) {
  const info=METRIC_INFO[metric];
  return <article className="metric-card">
    <div className="metric-card__label">{label??info?.label}{info&&<button type="button" className="help" aria-label={`About ${info.label}: ${info.help}`} data-tooltip={info.help} onKeyDown={event=>{if(event.key==="Escape")event.currentTarget.blur()}}><HelpCircle size={14} aria-hidden="true"/></button>}</div>
    <div className="metric-card__value">{metric?formatMetric(metric,value):value??EMPTY_VALUE}</div>
    {detail&&<div className="metric-card__detail">{detail}</div>}
  </article>;
}

export function ModelTypeBadge({ probabilistic }) { return <span className={`type-badge ${probabilistic?"type-badge--prob":""}`}>{probabilistic?"Probabilistic":"Deterministic"}</span>; }
export function Status({ ok, children }) { return <span className={`status ${ok?"status--ok":"status--error"}`} role="status" aria-live="polite">{ok?<CheckCircle2 size={14} aria-hidden="true"/>:<WifiOff size={14} aria-hidden="true"/>} {children}</span>; }
export function LoadingState({ label="Loading data…" }) { return <div className="state-box" role="status" aria-live="polite"><LoaderCircle className="spin" size={20} aria-hidden="true"/><span>{label}</span></div>; }
export function ErrorState({ message, onRetry, id }) { return message?<div id={id} className="state-box state-box--error" role="alert"><AlertCircle size={20} aria-hidden="true"/><span>{message}</span>{onRetry&&<button type="button" className="button button--secondary" onClick={onRetry}>Retry</button>}</div>:null; }
export function EmptyState({ title="No data available", detail }) { return <div className="state-box"><AlertCircle size={20} aria-hidden="true"/><div><strong>{title}</strong>{detail&&<p>{detail}</p>}</div></div>; }

export function Panel({ title, eyebrow, action, children, className="" }) { return <section className={`panel ${className}`}><header className="panel__header"><div>{eyebrow&&<p className="eyebrow">{eyebrow}</p>}<h2>{title}</h2></div>{action}</header>{children}</section>; }

export function ModelSelector({ models=[], value, onChange, id="model-selector" }) { return <label className="field" htmlFor={id}><span>Forecast model</span><select id={id} name="forecast_model" autoComplete="off" required value={value} onChange={event=>onChange(event.target.value)}>{models.map(model=><option key={model.model_id} value={model.model_id} disabled={!model.enabled}>{model.display_name}{!model.enabled?" — unavailable":""}</option>)}</select></label>; }
