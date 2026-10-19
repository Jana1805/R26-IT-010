import { useEffect, useState, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import axios from 'axios'
import {
  AlertTriangle, CheckCircle, Thermometer, Droplets, Wind,
  CloudRain, Sun, TrendingUp, Zap, Clock, Calendar, Users, Tag, Leaf,
  ArrowLeft, Info,
} from 'lucide-react'
import './LimeAnomalyDiagnosis.css'

const BI_DASHBOARD_URL = 'http://localhost:3000'

const LEVEL_META = {
  low    : { label: 'Low Demand',    className: 'lad-badge--low',    icon: CheckCircle  },
  medium : { label: 'Medium Demand', className: 'lad-badge--medium', icon: TrendingUp   },
  high   : { label: 'High Demand',   className: 'lad-badge--high',   icon: Zap          },
  peak   : { label: 'Peak Demand',   className: 'lad-badge--peak',   icon: AlertTriangle},
}

const FEATURE_ICONS = {
  'Temperature'         : Thermometer,
  'Humidity'            : Droplets,
  'Wind Speed'          : Wind,
  'Rainfall'            : CloudRain,
  'Solar Irradiance'    : Sun,
  'GDP'                 : TrendingUp,
  'Per Capita Energy Use': Leaf,
  'Electricity Price'   : Tag,
  'Day of Week'         : Calendar,
  'Hour of Day'         : Clock,
  'Month'               : Calendar,
  'Public Event'        : Users,
}

// Turns a failed /api/explain-date response into a message that says
// exactly why nothing is shown, instead of falling back to a sample instance.
function describeLiveError(status, date) {
  if (status === 404) return `No historical data for ${date} in the XAI demand dataset, so no explanation can be computed.`
  if (status === 422) return `"${date}" is not a valid date.`
  if (status === 503) return 'The live LIME explainer is unavailable on the server (model or dataset file missing).'
  return `Could not compute a live LIME explanation for ${date}. Is the XAI backend running on port 8000?`
}

function DemandBadge({ level }) {
  const meta = LEVEL_META[level] || LEVEL_META.medium
  const Icon = meta.icon
  return (
    <span className={`lad-badge ${meta.className}`}>
      <Icon size={10} />
      {meta.label}
    </span>
  )
}

function ConfidenceBar({ r2 }) {
  const pct   = Math.round(r2 * 100)
  const color = r2 >= 0.9 ? 'var(--green)' : r2 >= 0.75 ? 'var(--blue)' : 'var(--orange)'
  return (
    <div className="lad-conf">
      <div className="lad-conf-header">
        <span className="lad-conf-label">LIME Local Fit (R²)</span>
        <span className="lad-conf-value" style={{ color }}>{r2.toFixed(3)}</span>
      </div>
      <div className="lad-conf-track">
        <div className="lad-conf-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <p className="lad-conf-hint">
        {r2 >= 0.9
          ? 'Excellent — explanation closely matches model behaviour'
          : r2 >= 0.75
          ? 'Good — explanation is a reliable local approximation'
          : 'Moderate — interpretation should be treated with caution'}
      </p>
    </div>
  )
}

function ExplanationDetail({ instance, focused }) {
  const maxAbsWeight = Math.max(...instance.contributions.map(c => Math.abs(c.weight)), 0.001)
  const isLive = instance.source === 'live'
  const title  = isLive
    ? `Live LIME Explanation — ${instance.matched_date}`
    : `LIME Explanation — Instance #${String(instance.id).padStart(2, '0')}`

  return (
    <div className={`lad-panel lad-panel--detail ${focused ? 'lad-panel--focused' : ''}`}>
      <div className="lad-panel-header">
        <h2 className="lad-panel-title">{title}</h2>
        <DemandBadge level={instance.demand_level} />
      </div>

      <div className="lad-pred-row">
        <div className="lad-pred-block">
          <p className="lad-pred-label">Actual Demand</p>
          <p className="lad-pred-value">{instance.actual.toFixed(2)}</p>
          <p className="lad-pred-unit">kW</p>
        </div>
        <div className="lad-pred-block">
          <p className="lad-pred-label">XGB Predicted</p>
          <p className="lad-pred-value">{instance.predicted.toFixed(2)}</p>
          <p className="lad-pred-unit">kW</p>
        </div>
        <div className="lad-pred-block">
          <p className="lad-pred-label">Error</p>
          <p className="lad-pred-value lad-pred-value--error">
            {instance.error_kw > 0 ? '+' : ''}{instance.error_kw.toFixed(2)}
          </p>
          <p className="lad-pred-unit">{instance.error_pct.toFixed(2)}%</p>
        </div>
        <div className="lad-pred-block">
          <p className="lad-pred-label">Timestamp</p>
          <p className="lad-pred-ts">{instance.timestamp.slice(0, 16).replace('T', ' ')}</p>
        </div>
      </div>

      <ConfidenceBar r2={instance.lime_r2} />

      <div className="lad-contribs">
        <p className="lad-section-label">Feature Contributions</p>
        <div className="lad-contrib-list">
          {instance.contributions.map(c => {
            const Icon   = FEATURE_ICONS[c.feature] || Zap
            const barPct = (Math.abs(c.weight) / maxAbsWeight) * 100
            const isPos  = c.weight >= 0
            return (
              <div key={c.feature} className="lad-contrib-row">
                <div className="lad-contrib-meta">
                  <Icon size={12} className="lad-contrib-icon" />
                  <span className="lad-contrib-name">{c.rule || c.feature}</span>
                  <span className="lad-contrib-fval">(value {c.value})</span>
                  <span className={`lad-contrib-weight ${isPos ? 'lad-contrib-weight--pos' : 'lad-contrib-weight--neg'}`}>
                    {isPos ? '+' : ''}{c.weight.toFixed(4)} kW
                  </span>
                </div>
                <div className="lad-contrib-track">
                  <div
                    className={`lad-contrib-bar ${isPos ? 'lad-contrib-bar--pos' : 'lad-contrib-bar--neg'}`}
                    style={{ width: `${barPct}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </div>

      <div className="lad-intercept-row">
        <span>LIME intercept (baseline)</span>
        <span className="lad-intercept-val">{instance.intercept.toFixed(2)} kW</span>
      </div>
      {instance.local_pred != null && (
        <div className="lad-intercept-row">
          <span>LIME local prediction (intercept + contributions)</span>
          <span className="lad-intercept-val">{instance.local_pred.toFixed(2)} kW</span>
        </div>
      )}
    </div>
  )
}

export default function LimeAnomalyDiagnosis() {
  const [searchParams]               = useSearchParams()
  const fromBI                       = searchParams.get('source') === 'bi'
  // From Thanujan's "Future Behaviour Prediction" panel: date here is a real
  // historical day (the nearest pattern match), not the future date itself,
  // see FutureBehaviorPrediction.jsx / behavior_prediction.py matched_dates.
  const fromPrediction                = searchParams.get('source') === 'bi-predict'
  const biDate                       = searchParams.get('date')
  const futureDate                   = searchParams.get('future_date')

  const [data,       setData]       = useState(null)
  const [live,       setLive]       = useState(null)
  const [liveError,  setLiveError]  = useState(null)
  const [loading,    setLoading]    = useState(true)
  const [error,      setError]      = useState(null)
  const [selectedId, setSelectedId] = useState(1)
  const [filter,     setFilter]     = useState('all')

  useEffect(() => {
    // Any link from Behaviour Intelligence with a date gets a genuine live
    // LIME explanation for that date, never a lookup among the 15 samples.
    const wantsLive = (fromBI || fromPrediction) && biDate
    const liveRequest = wantsLive
      ? axios.get('/api/explain-date', { params: { date: biDate } })
          .then(r => ({ instance: { ...r.data, id: 0 } }))
          .catch(err => ({
            error: describeLiveError(err.response?.status, biDate),
          }))
      : Promise.resolve(null)

    Promise.all([axios.get('/api/anomaly-diagnosis'), liveRequest])
      .then(([listRes, liveRes]) => {
        setData(listRes.data)
        if (liveRes?.instance) {
          setLive(liveRes.instance)
          setSelectedId(0)
        } else if (liveRes?.error) {
          setLiveError(liveRes.error)
        }
        setLoading(false)
      })
      .catch(() => { setError('Could not load data. Is the XAI backend running on port 8000?'); setLoading(false) })
  }, [biDate, fromBI, fromPrediction])

  const instances = useMemo(() => {
    if (!data) return []
    return live ? [live, ...data.instances] : data.instances
  }, [data, live])

  const filtered = useMemo(() => (
    filter === 'all' ? instances : instances.filter(i => i.demand_level === filter)
  ), [instances, filter])

  const selected = useMemo(() => (
    instances.find(i => i.id === selectedId) || instances[0] || null
  ), [instances, selectedId])

  if (loading) return <div className="lad-state">Loading LIME data...</div>
  if (error)   return <div className="lad-state lad-state--error">{error}</div>

  const { meta } = data

  // Arriving from Thanujan's Behaviour Intelligence dashboard for one
  // specific day: show only the live explanation for that day, or say
  // clearly why there is none.
  if (fromBI) {
    let bannerMsg
    if (!biDate) {
      bannerMsg = 'No date was passed from Behaviour Intelligence, so there is no day to explain.'
    } else if (liveError) {
      bannerMsg = `Behaviour Intelligence flagged ${biDate}, but no explanation can be shown for it.`
    } else {
      bannerMsg = `Behaviour Intelligence flagged ${biDate}. Below is a live LIME explanation of the XGBoost `
        + `prediction for that day's highest-demand 15-minute reading (${live.timestamp.slice(11, 16)}).`
    }

    return (
      <div className="lad-page lad-page--focused">
        <div className="lad-bi-banner">
          <div className="lad-bi-banner-left">
            <ArrowLeft size={14} className="lad-bi-banner-icon" />
            <span className="lad-bi-banner-source">Behaviour Intelligence</span>
            <span className="lad-bi-banner-sep">·</span>
            <span className="lad-bi-banner-msg">{bannerMsg}</span>
          </div>
          <a href={BI_DASHBOARD_URL} className="lad-bi-banner-back">
            Back to Dashboard
          </a>
        </div>

        {liveError && (
          <div className="lad-notice">
            <Info size={14} />
            <span>{liveError}</span>
          </div>
        )}

        {live && (
          <>
            <ExplanationDetail instance={live} focused />
            <p className="lad-data-note">
              Demand values come from the XAI dataset (load_forecasting_dataset_corrected.csv),
              which is a different file from the one Behaviour Intelligence analyses, so the
              kW values for this date can differ between the two dashboards.
            </p>
          </>
        )}

        <a href={BI_DASHBOARD_URL} className="lad-focused-back-bottom">
          ← Back to Dashboard
        </a>
      </div>
    )
  }

  return (
    <div className="lad-page">

      {/* Prediction-flow context banner — shown when arriving from Thanujan's
          Future Behaviour Prediction, a new live instance sits at the top below */}
      {fromPrediction && biDate && (
        <div className="lad-bi-banner">
          <div className="lad-bi-banner-left">
            <ArrowLeft size={14} className="lad-bi-banner-icon" />
            <span className="lad-bi-banner-source">Behaviour Intelligence · Future Prediction</span>
            <span className="lad-bi-banner-sep">·</span>
            <span className="lad-bi-banner-msg">
              {liveError
                ? `${liveError} Showing the 15 saved sample instances only.`
                : futureDate
                ? `${futureDate} has no real feature data yet, showing a live explanation for the nearest real match, ${biDate}, at the top of the list.`
                : `Showing a live explanation for ${biDate} at the top of the list.`}
            </span>
          </div>
          <a href={BI_DASHBOARD_URL} className="lad-bi-banner-back">
            Back to Dashboard
          </a>
        </div>
      )}

      {/* Header */}
      <div className="lad-header">
        <span className="lad-component-tag">02</span>
        <div>
          <h1 className="lad-title">LIME Anomaly Diagnosis</h1>
          <p className="lad-subtitle">
            Select a prediction instance to see which features drove that specific forecast.
            LIME perturbs the input and fits a local linear model to explain the black-box prediction.
          </p>
        </div>
      </div>

      {/* Stats row */}
      <div className="lad-stats-row">
        <div className="lad-stat">
          <p className="lad-stat-label">Instances</p>
          <p className="lad-stat-value">{meta.sample_count}</p>
        </div>
        <div className="lad-stat">
          <p className="lad-stat-label">Mean Demand</p>
          <p className="lad-stat-value">{meta.mean_demand.toFixed(1)} <span className="lad-stat-unit">kW</span></p>
        </div>
        <div className="lad-stat">
          <p className="lad-stat-label">Std Demand</p>
          <p className="lad-stat-value">{meta.std_demand.toFixed(1)} <span className="lad-stat-unit">kW</span></p>
        </div>
        <div className="lad-stat">
          <p className="lad-stat-label">Peak Threshold (p90)</p>
          <p className="lad-stat-value">{meta.p90_threshold.toFixed(1)} <span className="lad-stat-unit">kW</span></p>
        </div>
      </div>

      <div className="lad-columns">

        {/* Left: Instance list */}
        <div className="lad-panel lad-panel--list">
          <div className="lad-panel-header">
            <h2 className="lad-panel-title">Prediction Instances</h2>
          </div>

          {/* Filter pills */}
          <div className="lad-filter-row">
            {['all', 'low', 'medium', 'high', 'peak'].map(f => (
              <button
                key={f}
                className={`lad-filter-pill ${filter === f ? 'lad-filter-pill--active' : ''}`}
                onClick={() => setFilter(f)}
              >
                {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>

          <div className="lad-instance-list">
            {filtered.map(inst => (
              <button
                key={inst.id}
                className={`lad-instance-card ${selectedId === inst.id ? 'lad-instance-card--active' : ''} ${inst.id === 0 ? 'lad-instance-card--live' : ''}`}
                onClick={() => setSelectedId(inst.id)}
              >
                <div className="lad-inst-top">
                  {inst.id === 0
                    ? <span className="lad-inst-id lad-inst-id--live">NEW</span>
                    : <span className="lad-inst-id">#{String(inst.id).padStart(2, '0')}</span>}
                  <DemandBadge level={inst.demand_level} />
                  <span className="lad-inst-r2">R²={inst.lime_r2.toFixed(2)}</span>
                </div>
                <div className="lad-inst-bottom">
                  <span className="lad-inst-ts">{inst.timestamp.slice(0, 16).replace('T', ' ')}</span>
                </div>
                <div className="lad-inst-demands">
                  <span>Actual: <strong>{inst.actual.toFixed(1)} kW</strong></span>
                  <span>Pred: <strong>{inst.predicted.toFixed(1)} kW</strong></span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Right: LIME explanation */}
        {selected && <ExplanationDetail instance={selected} />}

      </div>

      {/* Guide */}
      <div className="lad-guide">
        <p className="lad-guide-title">How to Read This</p>
        <div className="lad-guide-grid">
          <div className="lad-guide-card">
            <p className="lad-guide-card-title">LIME Weights</p>
            <p className="lad-guide-card-text">
              LIME splits each feature into quartile ranges. Each bar shows how much lying in the
              shown range (e.g. "Temperature &gt; 29.29") pushed this prediction up (green) or
              down (red). These are local effects, not global importances.
            </p>
          </div>
          <div className="lad-guide-card">
            <p className="lad-guide-card-title">Local Fit R²</p>
            <p className="lad-guide-card-text">
              LIME fits a linear model around the instance using 1000 perturbed samples.
              R² measures how well that linear model approximates the XGBoost prediction locally.
            </p>
          </div>
          <div className="lad-guide-card">
            <p className="lad-guide-card-title">Intercept &amp; Local Prediction</p>
            <p className="lad-guide-card-text">
              The intercept plus all contributions equals LIME's local prediction. The gap between
              that and the XGBoost prediction is the approximation error of the local linear model.
            </p>
          </div>
          <div className="lad-guide-card">
            <p className="lad-guide-card-title">Demand Levels</p>
            <p className="lad-guide-card-text">
              Low (&lt;p25), Medium (p25–p75), High (p75–p90), Peak (&gt;p90).
              Instances are sampled across all levels for diverse coverage.
            </p>
          </div>
        </div>
      </div>

    </div>
  )
}
