import { useEffect, useState } from 'react'
import axios from 'axios'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, Cell
} from 'recharts'
import { TrendingUp, TrendingDown, ArrowLeftRight, Zap } from 'lucide-react'
import './TemporalDrift.css'

const FEATURE_COLORS = {
  'Temperature':           '#ef4444',
  'Humidity':              '#3b82f6',
  'Wind Speed':            '#10b981',
  'Rainfall':              '#06b6d4',
  'Solar Irradiance':      '#f59e0b',
  'GDP':                   '#8b5cf6',
  'Per Capita Energy Use': '#ec4899',
  'Electricity Price':     '#f97316',
  'Day of Week':           '#84cc16',
  'Hour of Day':           '#a78bfa',
  'Month':                 '#14b8a6',
  'Public Event':          '#fb923c',
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const sorted = [...payload].sort((a, b) => b.value - a.value)
  return (
    <div className="chart-tooltip">
      <p className="tooltip-year">Year {label}</p>
      {sorted.map(p => (
        <div key={p.name} className="tooltip-row">
          <span className="tooltip-dot" style={{ background: p.color }} />
          <span className="tooltip-name">{p.name}</span>
          <span className="tooltip-val">{p.value.toFixed(4)}</span>
        </div>
      ))}
    </div>
  )
}

// Temperature's mean |SHAP| (~157 kW) is about 500x every other feature's,
// so it is hidden by default or the other lines sit flat at zero.
const DOMINANT_FEATURE = 'Temperature'

// Formats an error/score metric: tiny values in exponent form, null as a dash.
function fmtMetric(v, digits = 4) {
  if (v == null) return '—'
  if (v !== 0 && Math.abs(v) < 0.001) return v.toExponential(2)
  return v.toFixed(digits)
}

function rankColor(rank) {
  if (rank === 1) return '#f59e0b'
  if (rank === 2) return '#94a3b8'
  if (rank === 3) return '#f97316'
  return '#475569'
}

const GUIDE_ITEMS = [
  {
    Icon: TrendingUp,
    head: 'Rising Line',
    body: 'This feature is becoming a stronger driver of electricity demand. Planners should give it more weight in future planning.',
  },
  {
    Icon: TrendingDown,
    head: 'Falling Line',
    body: "This feature's influence on demand is weakening. Old models that relied heavily on it may be losing accuracy.",
  },
  {
    Icon: ArrowLeftRight,
    head: 'Crossing Lines',
    body: 'Two features swapped importance rank. This signals a structural shift in what drives demand — a key long-term planning signal.',
  },
  {
    Icon: Zap,
    head: 'SHAP Value',
    body: 'A higher SHAP value means a larger average impact on predicting load demand. Measured in the same units as demand (kW).',
  },
]

export default function TemporalDrift() {
  const [data, setData]             = useState(null)
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState(null)
  const [activeLines, setActiveLines] = useState({})
  const [driftExcludeDominant, setDriftExcludeDominant] = useState(true)

  useEffect(() => {
    axios.get('/api/temporal-drift')
      .then(res => {
        setData(res.data)
        const initial = {}
        res.data.features.forEach(f => { initial[f] = f !== DOMINANT_FEATURE })
        setActiveLines(initial)
        setLoading(false)
      })
      .catch(err => {
        setError(err.response?.data?.detail || 'Failed to load data. Run the notebook first.')
        setLoading(false)
      })
  }, [])

  if (loading) return (
    <div className="state-box">
      <div className="spinner" />
      <p>Computing SHAP analysis...</p>
    </div>
  )
  if (error) return (
    <div className="state-box state-error">
      <p>{error}</p>
    </div>
  )

  const lineData = data.years.map(year => {
    const row = { year: parseInt(year) }
    data.features.forEach(feat => { row[feat] = data.shap_by_year[year]?.[feat] ?? 0 })
    return row
  })

  const driftData = Object.entries(data.drift)
    .filter(([feature]) => !(driftExcludeDominant && feature === DOMINANT_FEATURE))
    .map(([feature, change]) => ({ feature, change: parseFloat(change.toFixed(4)) }))
    .sort((a, b) => b.change - a.change)

  const toggleLine = feat =>
    setActiveLines(prev => ({ ...prev, [feat]: !prev[feat] }))

  const { insights } = data
  const firstYear = data.years[0]
  const lastYear  = data.years[data.years.length - 1]

  // Largest yearly value of any feature other than the dominant one,
  // used in the note explaining why the dominant feature is hidden.
  const maxOtherShap = Math.max(...data.years.flatMap(y =>
    data.features.filter(f => f !== DOMINANT_FEATURE).map(f => data.shap_by_year[y]?.[f] ?? 0)
  ))
  const comparison  = data.model_comparison ? Object.entries(data.model_comparison) : []
  const performance = data.model_performance

  return (
    <div className="page">

      {/* ── Header ── */}
      <div className="page-header">
        <span className="page-tag">Component 01  SHAP</span>
        <h1 className="page-title">Temporal Drift Analysis</h1>
        <p className="page-sub">
          How the importance of each feature driving electricity demand has
          shifted year by year from {firstYear} to {lastYear}.
        </p>
      </div>

      {/* ── KPI Cards ── */}
      <div className="cards-row">
        <div className="card card--purple">
          <p className="card-label">Most Dominant Feature</p>
          <p className="card-value">{insights.most_dominant.feature}</p>
          <p className="card-sub">Avg SHAP  {insights.most_dominant.avg_shap}</p>
        </div>
        <div className="card card--green">
          <p className="card-label">Biggest Gainer</p>
          <p className="card-value">{insights.biggest_gainer.feature}</p>
          <p className="card-sub">
            +{insights.biggest_gainer.change.toFixed(4)} since {insights.biggest_gainer.from_year}
          </p>
        </div>
        <div className="card card--red">
          <p className="card-label">Biggest Decline</p>
          <p className="card-value">{insights.biggest_loser.feature}</p>
          <p className="card-sub">
            {insights.biggest_loser.change.toFixed(4)} since {insights.biggest_loser.from_year}
          </p>
        </div>
        <div className="card card--blue">
          <p className="card-label">Years Analysed</p>
          <p className="card-value">{data.years.length}</p>
          <p className="card-sub">{data.years.join(' · ')}</p>
        </div>
      </div>

      {/* ── Line Chart ── */}
      <div className="section">
        <div className="section-header">
          <h2 className="section-title">Feature Importance Over Time</h2>
          <p className="section-sub">Toggle features on/off to compare</p>
        </div>
        <div className="dominance-note">
          <strong>{DOMINANT_FEATURE} dominates.</strong> Its mean |SHAP| averages{' '}
          {insights.most_dominant.avg_shap.toFixed(1)} kW, while no other feature exceeds{' '}
          {maxOtherShap.toFixed(2)} kW in any year. It is hidden by default so the other
          features are readable; switch it on to see the full scale. Because the other
          features' values are so small, their year-to-year changes should be read with caution.
        </div>
        <div className="feature-toggles">
          {data.features.map(feat => (
            <button
              key={feat}
              className={`toggle-btn ${activeLines[feat] ? 'toggle-btn--on' : 'toggle-btn--off'}`}
              style={activeLines[feat] ? { borderColor: FEATURE_COLORS[feat], color: FEATURE_COLORS[feat] } : {}}
              onClick={() => toggleLine(feat)}
            >
              <span className="toggle-dot" style={{ background: activeLines[feat] ? FEATURE_COLORS[feat] : '#334155' }} />
              {feat}
            </button>
          ))}
        </div>
        <div className="chart-box">
          <ResponsiveContainer width="100%" height={380}>
            <LineChart data={lineData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#0F1E2E" />
              <XAxis dataKey="year" stroke="#1E293B" tick={{ fill: '#64748B', fontSize: 12, fontFamily: 'Fira Code' }} />
              <YAxis stroke="#1E293B" tick={{ fill: '#64748B', fontSize: 11, fontFamily: 'Fira Code' }}
                     label={{ value: 'Mean |SHAP|', angle: -90, position: 'insideLeft', fill: '#334155', fontSize: 11 }} />
              <Tooltip content={<CustomTooltip />} />
              {data.features.map(feat =>
                activeLines[feat] && (
                  <Line
                    key={feat}
                    type="monotone"
                    dataKey={feat}
                    stroke={FEATURE_COLORS[feat] || '#64748b'}
                    strokeWidth={2}
                    dot={{ r: 4, fill: FEATURE_COLORS[feat], strokeWidth: 0 }}
                    activeDot={{ r: 6 }}
                  />
                )
              )}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── Rankings ── */}
      <div className="section">
        <div className="section-header">
          <h2 className="section-title">Year-by-Year Feature Rankings</h2>
          <p className="section-sub">Top 5 demand drivers per year</p>
        </div>
        <div className="rankings-grid">
          {data.years.map(year => (
            <div key={year} className="rank-card">
              <p className="rank-year">{year}</p>
              {data.rankings_by_year[year].slice(0, 5).map(item => (
                <div key={item.feature} className="rank-row">
                  <span className="rank-badge" style={{ background: rankColor(item.rank) }}>
                    #{item.rank}
                  </span>
                  <span className="rank-feat">{item.feature}</span>
                  <span className="rank-val">{item.shap.toFixed(3)}</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* ── Drift Bar Chart ── */}
      <div className="section">
        <div className="section-header">
          <h2 className="section-title">Feature Drift  {firstYear} to {lastYear}</h2>
          <p className="section-sub">
            Blue = grew in importance    Red = declined in importance
          </p>
        </div>
        <div className="feature-toggles">
          <button
            className={`toggle-btn ${driftExcludeDominant ? 'toggle-btn--on' : 'toggle-btn--off'}`}
            onClick={() => setDriftExcludeDominant(v => !v)}
          >
            <span className="toggle-dot" style={{ background: driftExcludeDominant ? FEATURE_COLORS[DOMINANT_FEATURE] : '#334155' }} />
            Exclude {DOMINANT_FEATURE} ({data.drift[DOMINANT_FEATURE]?.toFixed(4)})
          </button>
        </div>
        <div className="chart-box">
          <ResponsiveContainer width="100%" height={360}>
            <BarChart data={driftData} layout="vertical" margin={{ top: 0, right: 40, left: 150, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#0F1E2E" horizontal={false} />
              <XAxis type="number" stroke="#1E293B" tick={{ fill: '#64748B', fontSize: 11, fontFamily: 'Fira Code' }}
                     tickFormatter={v => v.toFixed(3)} />
              <YAxis type="category" dataKey="feature" stroke="#1E293B"
                     tick={{ fill: '#94A3B8', fontSize: 12, fontFamily: 'Fira Sans' }} width={145} />
              <Tooltip
                formatter={v => [v.toFixed(4), 'SHAP Change']}
                contentStyle={{ background: '#0C1828', border: '1px solid #152235', borderRadius: 6, fontSize: 12 }}
                labelStyle={{ color: '#E2E8F0', fontFamily: 'Fira Code' }}
              />
              <Bar dataKey="change" radius={[0, 4, 4, 0]}>
                {driftData.map((entry, idx) => (
                  <Cell key={idx} fill={entry.change >= 0 ? '#3b82f6' : '#ef4444'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── Model Comparison ── */}
      {comparison.length > 0 && (
        <div className="section">
          <div className="section-header">
            <h2 className="section-title">Forecasting Model Comparison</h2>
            <p className="section-sub">
              Same chronological 80/20 split
              {performance ? ` (train ${performance.train_size.toLocaleString()} / test ${performance.test_size.toLocaleString()} rows)` : ''}
              , test-set metrics
            </p>
          </div>
          <div className="chart-box table-box">
            <table className="cmp-table">
              <thead>
                <tr>
                  <th>Model</th>
                  <th>Test RMSE (kW)</th>
                  <th>Test MAE (kW)</th>
                  <th>Test R²</th>
                  <th>Train time (s)</th>
                </tr>
              </thead>
              <tbody>
                {comparison.map(([name, m]) => (
                  <tr key={name} className={name.startsWith('XGBoost') ? 'cmp-row--explained' : ''}>
                    <td>{name}{name.startsWith('XGBoost') ? '  (explained model)' : ''}</td>
                    <td>{fmtMetric(m.rmse)}</td>
                    <td>{fmtMetric(m.mae)}</td>
                    <td>{fmtMetric(m.r2, 6)}</td>
                    <td>{m.train_seconds == null ? 'not recorded' : m.train_seconds.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {performance && (
            <div className="chart-box table-box">
              <table className="cmp-table">
                <thead>
                  <tr>
                    <th>XGBoost (Optuna-tuned)</th>
                    <th>RMSE (kW)</th>
                    <th>MAE (kW)</th>
                    <th>R²</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>Train</td>
                    <td>{fmtMetric(performance.train_rmse)}</td>
                    <td>{fmtMetric(performance.train_mae)}</td>
                    <td>{fmtMetric(performance.train_r2)}</td>
                  </tr>
                  <tr>
                    <td>Test</td>
                    <td>{fmtMetric(performance.test_rmse)}</td>
                    <td>{fmtMetric(performance.test_mae)}</td>
                    <td>{fmtMetric(performance.test_r2)}</td>
                  </tr>
                </tbody>
              </table>
              <p className="cmp-foot">
                Optuna: {performance.optuna_trials} trials, best validation RMSE{' '}
                {fmtMetric(performance.best_val_rmse)} kW.
              </p>
            </div>
          )}

          <p className="cmp-note">
            Linear Regression has almost exactly zero error because in this dataset Load Demand
            is a linear function of Temperature. XGBoost is still the model explained here: SHAP's
            TreeExplainer computes exact Shapley values for tree models, and a tree model can also
            capture the non-linear effects expected in real metered demand data.
          </p>
        </div>
      )}

      {/* ── Guide ── */}
      <div className="section">
        <div className="section-header">
          <h2 className="section-title">How to Read This</h2>
        </div>
        <div className="guide-grid">
          {GUIDE_ITEMS.map(({ Icon, head, body }) => (
            <div key={head} className="guide-card">
              <div className="guide-icon-wrap">
                <Icon size={15} />
              </div>
              <p className="guide-head">{head}</p>
              <p className="guide-body">{body}</p>
            </div>
          ))}
        </div>
      </div>

    </div>
  )
}
