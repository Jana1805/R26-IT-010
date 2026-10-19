import { useEffect, useState } from 'react'
import axios from 'axios'
import './TemporalDrift.css'
import './ModelXaiComparison.css'

const FIG = name => `/api/figures/${name}`

// Formats a metric: tiny values in exponent form, null as a dash.
function fmt(v, digits = 4) {
  if (v == null) return '—'
  if (v !== 0 && Math.abs(v) < 0.001) return v.toExponential(2)
  return v.toFixed(digits)
}

function Figure({ name, alt, caption, narrow }) {
  return (
    <figure className={`mx-figure ${narrow ? 'mx-figure--narrow' : ''}`}>
      <img src={FIG(name)} alt={alt} loading="lazy" />
      {caption && <figcaption>{caption}</figcaption>}
    </figure>
  )
}

function Note({ children }) {
  return <p className="mx-note">{children}</p>
}

function ModelSection({ mc }) {
  const holdout = Object.entries(mc.holdout)
  const cv = Object.entries(mc.cross_validation.results)
  return (
    <div className="section">
      <div className="section-header">
        <h2 className="section-title">A · Forecasting models</h2>
        <p className="section-sub">
          Same IQR cleaning and chronological 80/20 split as notebook 1
          (train {mc.split.train_rows.toLocaleString()} / test {mc.split.test_rows.toLocaleString()} rows,
          test {mc.split.test_start.slice(0, 10)} → {mc.split.test_end.slice(0, 10)})
        </p>
      </div>
      <div className="chart-box table-box">
        <table className="cmp-table">
          <thead>
            <tr>
              <th>Model</th><th>RMSE (kW)</th><th>MAE (kW)</th><th>MAPE (%)</th><th>R²</th>
              <th>Train (s)</th><th>Tuning (s)</th><th>Inference (ms / 1,000 rows)</th>
            </tr>
          </thead>
          <tbody>
            {holdout.map(([name, m]) => (
              <tr key={name} className={name.startsWith('XGBoost') ? 'cmp-row--explained' : ''}>
                <td>{name}</td>
                <td>{fmt(m.rmse)}</td>
                <td>{fmt(m.mae)}</td>
                <td>{fmt(m.mape, 3)}</td>
                <td>{fmt(m.r2, 6)}</td>
                <td>{fmt(m.train_seconds, 2)}</td>
                <td>{m.tuning_seconds == null ? 'see notebook 1' : fmt(m.tuning_seconds, 1)}</td>
                <td>{fmt(m.inference_ms_per_1000, 3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Figure name="model_comparison_rmse_mape.png" alt="Bar charts of test RMSE and MAPE per model, log scale" />

      <div className="section-header mx-subhead">
        <h3 className="section-title">5-fold rolling-origin cross-validation (mean ± std)</h3>
        <p className="section-sub">{mc.cross_validation.method}</p>
      </div>
      <div className="chart-box table-box">
        <table className="cmp-table">
          <thead>
            <tr><th>Model</th><th>RMSE (kW)</th><th>MAE (kW)</th><th>MAPE (%)</th><th>R²</th></tr>
          </thead>
          <tbody>
            {cv.map(([name, r]) => (
              <tr key={name} className={name.startsWith('XGBoost') ? 'cmp-row--explained' : ''}>
                <td>{name}</td>
                <td>{fmt(r.rmse.mean)} ± {fmt(r.rmse.std)}</td>
                <td>{fmt(r.mae.mean)} ± {fmt(r.mae.std)}</td>
                <td>{fmt(r.mape.mean, 3)} ± {fmt(r.mape.std, 3)}</td>
                <td>{fmt(r.r2.mean, 6)} ± {fmt(r.r2.std, 6)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Note>
        Random Forest was tuned with exactly the same Optuna budget as XGBoost (50 trials, same
        10,000-row subsample, same validation split), so the comparison is fair. The seasonal-naive
        baseline (the reading one week earlier) shows what “no model” achieves. XGBoost metrics come
        from the deployed <code>xgb_model.pkl</code>; its training time was measured on a throw-away
        refit with identical settings.
      </Note>
    </div>
  )
}

function XaiSection({ xc }) {
  const g = xc.ground_truth
  const f = xc.fidelity
  return (
    <div className="section">
      <div className="section-header">
        <h2 className="section-title">B · SHAP vs LIME on the deployed XGBoost</h2>
        <p className="section-sub">Scored against the known ground truth: only Temperature matters, at +100 kW per °C</p>
      </div>
      <div className="chart-box table-box">
        <table className="cmp-table">
          <thead><tr><th>Criterion</th><th>SHAP TreeExplainer</th><th>LIME (1,000 samples)</th></tr></thead>
          <tbody>
            {xc.table_rows.map(([crit, s, l]) => (
              <tr key={crit}><td>{crit}</td><td>{s}</td><td>{l}</td></tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mx-grid">
        <Figure
          name="shap_dependence_temperature.png"
          alt="SHAP value for Temperature against temperature, lying on the true straight line"
          caption={`Visual proof of correctness: every SHAP value lies on the true line 100 × (T − mean T). Pearson r = ${g.shap_temperature_vs_truth_pearson_r.toFixed(5)}.`}
        />
        <Figure
          name="shap_bar.png"
          alt="Mean absolute SHAP per feature"
          caption={`${g.shap_pct_attribution_on_temperature.toFixed(2)}% of all SHAP attribution goes to Temperature, matching the ground truth that the other 11 features have no effect.`}
        />
      </div>
      <Figure narrow name="shap_beeswarm.png" alt="SHAP beeswarm plot" caption="Beeswarm: high temperatures (red) push demand up, low temperatures (blue) push it down; every other feature sits at zero." />

      <div className="section-header mx-subhead">
        <h3 className="section-title">LIME fidelity by demand level ({g.n_instances_lime} test instances)</h3>
      </div>
      <div className="chart-box table-box">
        <table className="cmp-table">
          <thead>
            <tr><th>Level</th><th>n</th><th>LIME R² mean (min–max)</th><th>|LIME local − XGBoost| mean / max (kW)</th><th>Temperature ranked #1</th></tr>
          </thead>
          <tbody>
            {Object.entries(f.by_level).map(([lv, r]) => (
              <tr key={lv}>
                <td>{lv}</td>
                <td>{r.n}</td>
                <td>{r.lime_r2_mean.toFixed(3)} ({r.lime_r2_min.toFixed(3)}–{r.lime_r2_max.toFixed(3)})</td>
                <td>{r.lime_abs_localpred_minus_pred_mean_kw.toFixed(1)} / {r.lime_abs_localpred_minus_pred_max_kw.toFixed(1)}</td>
                <td>{r.lime_temperature_rank1_pct.toFixed(0)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mx-grid">
        <Figure name="lime_example_peak.png" alt="LIME explanation for a peak-demand instance" />
        <Figure name="lime_example_low.png" alt="LIME explanation for a low-demand instance" />
      </div>
      <Figure name="lime_stability_box.png" alt="Box plot of LIME Temperature weight across 10 seeds per instance" />
      <Note>
        SHAP is exact and deterministic for tree models: base value + contributions reproduces every
        prediction (max error {fmt(f.shap_additivity_abs_error_max_kw)} kW). LIME approximates the model with a
        local linear fit on quartile bins of each feature. It always finds Temperature, but its weights
        move with the random seed and its fit is weakest for medium demand, where temperatures fall in
        the two middle bins. On ranks 2–12 the two methods disagree, which is expected: those features
        have zero true effect, so their order is noise in both.
      </Note>
    </div>
  )
}

function DriftSection({ td }) {
  const flagged = td.flagged_first_to_last
  const v1 = td.v1_comparison
  const lastYear = td.years[td.years.length - 1]
  const tempLast = td.per_year[lastYear].mean_abs_shap.Temperature
  const flaggedText = flagged.map(f => {
    const c = td.drift[f].change_first_to_last_kw
    return `${f} (${c >= 0 ? '+' : ''}${fmt(c, 4)} kW, ${(Math.abs(c) / tempLast * 100).toFixed(4)}% of Temperature's importance)`
  }).join(', ')
  return (
    <div className="section">
      <div className="section-header">
        <h2 className="section-title">C · Temporal drift with confidence intervals</h2>
        <p className="section-sub">{td.method}</p>
      </div>
      <Figure name="temporal_drift_v2.png" alt="Mean absolute SHAP per year with 95% confidence bands, one panel per feature" />
      <div className="chart-box table-box">
        <table className="cmp-table">
          <thead>
            <tr><th>Feature</th><th>{td.years[0]} mean |SHAP| (95% CI)</th><th>{td.years[td.years.length - 1]} mean |SHAP| (95% CI)</th><th>Drift flagged?</th></tr>
          </thead>
          <tbody>
            {td.features.map(feat => {
              const a = td.per_year[td.years[0]]
              const b = td.per_year[td.years[td.years.length - 1]]
              const ci = (y, d) => `${fmt(y.mean_abs_shap[feat], d)} (${fmt(y.ci_low[feat], d)}–${fmt(y.ci_high[feat], d)})`
              const digits = feat === 'Temperature' ? 2 : 4
              return (
                <tr key={feat}>
                  <td>{feat}</td>
                  <td>{ci(a, digits)}</td>
                  <td>{ci(b, digits)}</td>
                  <td>{td.drift[feat].flagged_first_to_last ? 'yes (CIs do not overlap)' : 'no'}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <Note>
        {flagged.length
          ? `Flagged ${td.years[0]} → ${lastYear}: ${flaggedText}. A flag means the change is statistically real, `
            + `not that it matters: ${lastYear} only covers January–May, so its mix of months and temperatures differs. `
          : `No feature shows drift between ${td.years[0]} and ${lastYear}. `}
        The earlier analysis refitted a new model on 2,000 rows per year and reported
        “{v1.v1_biggest_gainer.feature}” as the biggest gainer and “{v1.v1_biggest_loser.feature}” as the biggest decline.
        With one fixed model and confidence intervals, {v1.v1_biggest_gainer.feature} is
        {v1.v1_gainer_flagged_in_v2 ? '' : ' not'} flagged and {v1.v1_biggest_loser.feature} is
        {v1.v1_loser_flagged_in_v2 ? '' : ' not'} flagged. Because the model is fixed, any flagged change
        reflects that year’s input data (for example a different spread of temperatures), not a change in the model.
      </Note>
    </div>
  )
}

export default function ModelXaiComparison() {
  const [mc, setMc] = useState(null)
  const [xc, setXc] = useState(null)
  const [td, setTd] = useState(null)
  const [errors, setErrors] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const calls = [
      ['/api/v2/model-comparison', setMc],
      ['/api/v2/xai-comparison', setXc],
      ['/api/v2/temporal-drift', setTd],
    ]
    Promise.allSettled(calls.map(([url]) => axios.get(url))).then(results => {
      const errs = []
      results.forEach((r, i) => {
        if (r.status === 'fulfilled') calls[i][1](r.value.data)
        else errs.push(`${calls[i][0]}: ${r.reason.response?.data?.detail || 'request failed'}`)
      })
      setErrors(errs)
      setLoading(false)
    })
  }, [])

  if (loading) return (
    <div className="state-box"><div className="spinner" /><p>Loading comparison results...</p></div>
  )

  return (
    <div className="page">
      <div className="page-header">
        <span className="page-tag">Component 03  Evidence</span>
        <h1 className="page-title">Model &amp; XAI Comparison</h1>
        <p className="page-sub">
          Which forecasting model, which explanation method, and how far each can be trusted.
        </p>
      </div>

      <div className="dominance-note mx-intro">
        <strong>Why Linear Regression is exact here, and why that helps.</strong> In this dataset
        demand is exactly 100 × Temperature − 1300; the other 11 features have no effect at all.
        A straight-line model therefore fits perfectly, so accuracy cannot separate the models.
        But it also means the <em>true</em> explanation is known, which lets us check SHAP and LIME
        against the right answer instead of trusting them blindly.
      </div>

      {errors.length > 0 && (
        <div className="state-box state-error mx-errors">
          {errors.map(e => <p key={e}>{e}</p>)}
        </div>
      )}

      {mc && <ModelSection mc={mc} />}
      {xc && <XaiSection xc={xc} />}
      {td && <DriftSection td={td} />}
    </div>
  )
}
