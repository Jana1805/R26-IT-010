import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, Cell,
} from 'recharts';
import { formatScore, formatPercent } from './format.js';

const BASE_URL = 'http://127.0.0.1:8001';

function ModelCard({ model, isBest }) {
  const notApplicable = model.status === 'Not applicable - flags no days';
  return (
    <div className={`model-card ${isBest ? 'model-card-best' : ''}`}>
      <div className="model-card-header">
        <h3 className="model-card-name">{model.model_name}</h3>
        {isBest && <span className="model-card-badge">Best Model</span>}
      </div>
      <p className="model-card-type">{model.model_type}</p>
      <p className="model-card-description">{model.description}</p>
      {notApplicable && <p className="status-na">{model.status}</p>}
      <div className="model-card-metrics">
        <div className="model-card-metric">
          <span className="metric-label">Anomaly rate</span>
          <span className="metric-value">{formatPercent(model.anomaly_percentage)}</span>
        </div>
        <div className="model-card-metric">
          <span className="metric-label">Anomaly count</span>
          <span className="metric-value">{model.anomaly_count}</span>
        </div>
        <div className="model-card-metric">
          <span className="metric-label">Mean Jaccard</span>
          <span className="metric-value">{formatScore(model.mean_jaccard, 3)}</span>
        </div>
      </div>
    </div>
  );
}

export default function AnomalyComparison() {
  const [comparisonData, setComparisonData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    axios
      .get(`${BASE_URL}/api/anomaly-comparison`)
      .then((res) => {
        setComparisonData(res.data.data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.response?.data?.message || 'Failed to load anomaly comparison');
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner" />
        <p>Running bootstrap stability comparison…</p>
        <p className="section-meta">20 resamples × 4 models — this can take up to 15 seconds</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-screen">
        <h2>Cannot load anomaly comparison</h2>
        <p>{error}</p>
      </div>
    );
  }

  const {
    models,
    best_model,
    explanation,
    summary_points,
    comparison_table,
    spearman_matrix,
    contamination_note,
    bootstrap_config,
    runtime_seconds,
    total_days,
  } = comparisonData;

  const bestModelName = best_model ? best_model.model_name : null;
  const spearmanModels = Object.keys(spearman_matrix);
  const resamplePct = Math.round(bootstrap_config.resample_frac * 100);

  const jaccardData = comparison_table.map((row) => ({
    model: row.model,
    jaccard: row.mean_jaccard,
  }));

  const symDiffData = comparison_table.map((row) => ({
    model: row.model,
    diff: row.mean_symmetric_difference,
  }));

  return (
    <div className="app">
      {/* ── Header ── */}
      <header className="app-header">
        <div className="app-header-inner">
          <div className="app-header-brand">
            <h1 className="app-header-title">Anomaly Detection Comparison</h1>
            <p className="app-header-sub">
              Models are ranked by bootstrap stability — how consistently each flagged set survives resampling — not by anomaly rate.
            </p>
            <span className="app-context-indicator">
              {total_days} days · {bootstrap_config.n_resamples} resamples ({resamplePct}%) · {runtime_seconds}s
            </span>
          </div>
        </div>
      </header>

      <main className="app-main">
        {/* ── Model Overview Cards ── */}
        <section className="model-cards-section">
          <h2 className="section-title">Model overview</h2>
          <div className="model-cards-grid">
            {models.map((model) => (
              <ModelCard
                key={model.model_name}
                model={model}
                isBest={model.status === 'Best Model'}
              />
            ))}
          </div>
        </section>

        {/* ── Methodology Note ── */}
        <div className="note-callout">
          <span className="note-callout-icon">ⓘ</span>
          <div>
            <span className="note-callout-label">Methodology note</span>
            {contamination_note}
          </div>
        </div>

        {/* ── Why This Model Section ── */}
        <section className="why-model-section">
          <h2 className="section-title">
            {best_model ? `Why ${best_model.model_name} was selected` : 'No model selected'}
          </h2>
          <div className="why-model-content">
            <p className="why-model-explanation">{explanation}</p>
          </div>
        </section>

        {/* ── Comparison Table ── */}
        <section className="comparison-table-section">
          <h2 className="section-title">Side-by-side comparison</h2>
          <div className="table-wrapper">
            <table className="data-table comparison-table">
              <thead>
                <tr>
                  <th>Metric</th>
                  {comparison_table.map((row) => (
                    <th key={row.model} className={row.status === 'Best Model' ? 'best-model-header' : ''}>
                      {row.model}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="metric-name">
                    Anomaly count
                    <span className="metric-direction">Number of detected anomalies</span>
                  </td>
                  {comparison_table.map((row) => (
                    <td key={row.model} className={row.status === 'Best Model' ? 'best-model-cell' : ''}>
                      {row.anomaly_count}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="metric-name">
                    Anomaly percentage
                    <span className="metric-direction">Reported only — not used for ranking</span>
                  </td>
                  {comparison_table.map((row) => (
                    <td key={row.model} className={row.status === 'Best Model' ? 'best-model-cell' : ''}>
                      {formatPercent(row.anomaly_percentage)}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="metric-name">
                    Mean anomaly score
                    <span className="metric-direction">Average anomaly score</span>
                  </td>
                  {comparison_table.map((row) => (
                    <td key={row.model} className={row.status === 'Best Model' ? 'best-model-cell' : ''}>
                      {formatScore(row.mean_anomaly_score)}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="metric-name">
                    Std anomaly score
                    <span className="metric-direction">Score variance</span>
                  </td>
                  {comparison_table.map((row) => (
                    <td key={row.model} className={row.status === 'Best Model' ? 'best-model-cell' : ''}>
                      {formatScore(row.std_anomaly_score)}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="metric-name">
                    Mean Jaccard
                    <span className="metric-direction">Higher is more stable under resampling</span>
                  </td>
                  {comparison_table.map((row) => (
                    <td key={row.model} className={row.status === 'Best Model' ? 'best-model-cell' : ''}>
                      {formatScore(row.mean_jaccard)}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="metric-name">
                    Std Jaccard
                    <span className="metric-direction">Variance across resamples</span>
                  </td>
                  {comparison_table.map((row) => (
                    <td key={row.model} className={row.status === 'Best Model' ? 'best-model-cell' : ''}>
                      {formatScore(row.std_jaccard)}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="metric-name">
                    Mean symmetric difference
                    <span className="metric-direction">Days differing per resample — lower is more stable</span>
                  </td>
                  {comparison_table.map((row) => (
                    <td key={row.model} className={row.status === 'Best Model' ? 'best-model-cell' : ''}>
                      {row.mean_symmetric_difference}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="metric-name">Overall rank</td>
                  {comparison_table.map((row) => (
                    <td
                      key={row.model}
                      className={row.rank === null ? 'rank-cell rank-na' : `rank-cell rank-${row.rank}`}
                    >
                      {row.rank === null ? <span className="status-na">N/A</span> : row.rank}
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        {/* ── Visual Comparison ── */}
        <section className="visual-comparison-section">
          <h2 className="section-title">Stability comparison</h2>
          <div className="charts-row">
            <div className="chart-card">
              <h3 className="chart-title">Mean Jaccard vs full-data flagged set</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={jaccardData} margin={{ top: 20, right: 20, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="model" tick={{ fontSize: 11, fill: 'var(--text-sub)' }} angle={-45} textAnchor="end" height={80} />
                  <YAxis domain={[0, 1]} tick={{ fontSize: 12, fill: 'var(--text-sub)' }} />
                  <Tooltip formatter={(v) => [formatScore(v), 'Mean Jaccard']} />
                  <Bar dataKey="jaccard" radius={[4, 4, 0, 0]}>
                    {jaccardData.map((entry) => (
                      <Cell key={entry.model} fill={entry.model === bestModelName ? 'var(--accent)' : 'var(--text-sub)'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="chart-card">
              <h3 className="chart-title">Mean symmetric difference (days)</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={symDiffData} margin={{ top: 20, right: 20, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="model" tick={{ fontSize: 11, fill: 'var(--text-sub)' }} angle={-45} textAnchor="end" height={80} />
                  <YAxis tick={{ fontSize: 12, fill: 'var(--text-sub)' }} />
                  <Tooltip formatter={(v) => [v, 'Days differing']} />
                  <Bar dataKey="diff" radius={[4, 4, 0, 0]}>
                    {symDiffData.map((entry) => (
                      <Cell key={entry.model} fill={entry.model === bestModelName ? 'var(--accent)' : 'var(--text-sub)'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </section>

        {/* ── Ranking Section ── */}
        <section className="ranking-section">
          <h2 className="section-title">Model ranking — bootstrap stability</h2>
          <p className="section-meta">
            Ranked by mean Jaccard across {bootstrap_config.n_resamples} resamples of {resamplePct}% of days (seeds {bootstrap_config.seeds}).
          </p>
          <div className="ranking-list">
            {models.map((model) => (
              <div
                key={model.model_name}
                className={model.rank === null ? 'ranking-item rank-na' : `ranking-item rank-${model.rank}`}
              >
                <span className="ranking-rank">
                  {model.rank === null ? '—' : model.rank}
                </span>
                <span className="ranking-name">{model.model_name}</span>
                {model.rank === 1 && <span className="rank-marker">Selected</span>}
                {model.rank === null && <span className="status-na">{model.status}</span>}
              </div>
            ))}
          </div>
        </section>

        {/* ── Spearman Diagnostic Section ── */}
        <section className="comparison-table-section">
          <h2 className="section-title">
            Rank-order agreement (Spearman)
            <span className="diagnostic-tag">Diagnostic — not used for ranking</span>
          </h2>
          <p className="section-meta">
            Pairwise Spearman correlation between each model's continuous anomaly score (oriented higher = more anomalous), across all {total_days} days. Measures whether models agree on the ordering of abnormality, independent of any cutoff.
          </p>
          <div className="table-wrapper">
            <table className="data-table matrix-table">
              <thead>
                <tr>
                  <th></th>
                  {spearmanModels.map((name) => (
                    <th key={name}>{name}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {spearmanModels.map((rowName) => (
                  <tr key={rowName}>
                    <td className="metric-name">{rowName}</td>
                    {spearmanModels.map((colName) => (
                      <td key={colName} className={rowName === colName ? 'matrix-diagonal' : ''}>
                        {formatScore(spearman_matrix[rowName][colName])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* ── Best Model Summary ── */}
        {best_model ? (
          <section className="best-model-summary-section">
            <h2 className="section-title">Selected model</h2>
            <div className="best-model-summary">
              <div className="best-model-header">
                <h3 className="best-model-name">{best_model.model_name}</h3>
                <span className="best-model-badge">Selected</span>
              </div>
              <div className="best-model-why">
                <h4>Why</h4>
                <ul className="best-model-points">
                  {summary_points.map((point, index) => (
                    <li key={index}>{point}</li>
                  ))}
                </ul>
              </div>
            </div>
          </section>
        ) : (
          <section className="best-model-summary-section">
            <h2 className="section-title">Selected model</h2>
            <p className="why-model-explanation">No model could be ranked — see the explanation above.</p>
          </section>
        )}
      </main>
    </div>
  );
}
