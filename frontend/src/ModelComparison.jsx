import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, Cell,
} from 'recharts';
import { formatScore } from './format.js';

const BASE_URL = 'http://127.0.0.1:8001';

function ModelCard({ model, isBest }) {
  const notApplicable = model.status === 'Not applicable - single cluster';
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
          <span className="metric-label">Silhouette</span>
          <span className="metric-value">{formatScore(model.silhouette_score)}</span>
        </div>
        <div className="model-card-metric">
          <span className="metric-label">DB index</span>
          <span className="metric-value">{formatScore(model.davies_bouldin_index)}</span>
        </div>
        <div className="model-card-metric">
          <span className="metric-label">Mean rank</span>
          <span className="metric-value">{model.mean_rank != null ? model.mean_rank : '—'}</span>
        </div>
        {model.eps != null && (
          <div className="model-card-metric">
            <span className="metric-label">Eps (knee)</span>
            <span className="metric-value">{formatScore(model.eps)}</span>
          </div>
        )}
        {model.knee_percentile != null && (
          <div className="model-card-metric">
            <span className="metric-label">Knee percentile</span>
            <span className="metric-value">{model.knee_percentile}%</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ModelComparison() {
  const [comparisonData, setComparisonData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    axios
      .get(`${BASE_URL}/api/model-comparison`)
      .then((res) => {
        setComparisonData(res.data.data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.response?.data?.message || 'Failed to load model comparison');
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner" />
        <p>Loading model comparison…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-screen">
        <h2>Cannot load model comparison</h2>
        <p>{error}</p>
      </div>
    );
  }

  const { models, best_model, explanation, summary_points, comparison_table } = comparisonData;
  const bestModelName = best_model ? best_model.model_name : null;

  // Prepare chart data — DBSCAN's metrics are null/"N/A" (single cluster on
  // this dataset), so it's excluded from these numeric charts rather than
  // plotting a non-numeric value.
  const silhouetteData = comparison_table
    .filter(row => row.silhouette_score !== 'N/A')
    .map(row => ({ model: row.model, score: row.silhouette_score }));

  const dbiData = comparison_table
    .filter(row => row.davies_bouldin_index !== 'N/A')
    .map(row => ({ model: row.model, score: row.davies_bouldin_index }));

  return (
    <div className="app">
      {/* ── Header ── */}
      <header className="app-header">
        <div className="app-header-inner">
          <div className="app-header-brand">
            <h1 className="app-header-title">Model Comparison</h1>
            <p className="app-header-sub">
              Clustering algorithms ranked by mean rank across Silhouette, Davies-Bouldin, and Calinski-Harabasz.
            </p>
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

        {/* ── Why This Model Section ── */}
        <section className="why-model-section">
          <h2 className="section-title">Why {best_model.model_name} was selected</h2>
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
                    Silhouette score
                    <span className="metric-direction">Higher is better</span>
                  </td>
                  {comparison_table.map((row) => (
                    <td key={row.model} className={row.status === 'Best Model' ? 'best-model-cell' : ''}>
                      {formatScore(row.silhouette_score)}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="metric-name">
                    Silhouette rank
                    <span className="metric-direction">1 = best</span>
                  </td>
                  {comparison_table.map((row) => (
                    <td key={row.model} className={row.status === 'Best Model' ? 'best-model-cell' : ''}>
                      {row.silhouette_rank ?? '—'}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="metric-name">
                    Davies-Bouldin index
                    <span className="metric-direction">Lower is better</span>
                  </td>
                  {comparison_table.map((row) => (
                    <td key={row.model} className={row.status === 'Best Model' ? 'best-model-cell' : ''}>
                      {formatScore(row.davies_bouldin_index)}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="metric-name">
                    Davies-Bouldin rank
                    <span className="metric-direction">1 = best</span>
                  </td>
                  {comparison_table.map((row) => (
                    <td key={row.model} className={row.status === 'Best Model' ? 'best-model-cell' : ''}>
                      {row.davies_bouldin_rank ?? '—'}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="metric-name">
                    Calinski-Harabasz score
                    <span className="metric-direction">Higher is better</span>
                  </td>
                  {comparison_table.map((row) => (
                    <td key={row.model} className={row.status === 'Best Model' ? 'best-model-cell' : ''}>
                      {formatScore(row.calinski_harabasz_score, 2)}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="metric-name">
                    Calinski-Harabasz rank
                    <span className="metric-direction">1 = best</span>
                  </td>
                  {comparison_table.map((row) => (
                    <td key={row.model} className={row.status === 'Best Model' ? 'best-model-cell' : ''}>
                      {row.calinski_harabasz_rank ?? '—'}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="metric-name">
                    Mean rank
                    <span className="metric-direction">Average of the three ranks above — lower is better</span>
                  </td>
                  {comparison_table.map((row) => (
                    <td key={row.model} className={row.status === 'Best Model' ? 'best-model-cell' : ''}>
                      {row.mean_rank}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="metric-name">Number of clusters</td>
                  {comparison_table.map((row) => (
                    <td key={row.model}>{row.n_clusters}</td>
                  ))}
                </tr>
                <tr>
                  <td className="metric-name">Noise points</td>
                  {comparison_table.map((row) => (
                    <td key={row.model}>{row.noise_points}</td>
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
          <h2 className="section-title">Performance comparison</h2>
          <div className="charts-row">
            <div className="chart-card">
              <h3 className="chart-title">Silhouette score (higher is better)</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={silhouetteData} margin={{ top: 20, right: 20, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="model" tick={{ fontSize: 11, fill: 'var(--text-sub)' }} angle={-45} textAnchor="end" height={80} />
                  <YAxis tick={{ fontSize: 12, fill: 'var(--text-sub)' }} />
                  <Tooltip formatter={(v) => [formatScore(v), 'Score']} />
                  <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                    {silhouetteData.map((entry) => (
                      <Cell key={entry.model} fill={entry.model === bestModelName ? 'var(--accent)' : 'var(--text-sub)'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="chart-card">
              <h3 className="chart-title">Davies-Bouldin index (lower is better)</h3>
              {dbiData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={dbiData} margin={{ top: 20, right: 20, left: 20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis dataKey="model" tick={{ fontSize: 11, fill: 'var(--text-sub)' }} angle={-45} textAnchor="end" height={80} />
                    <YAxis tick={{ fontSize: 12, fill: 'var(--text-sub)' }} />
                    <Tooltip formatter={(v) => [formatScore(v), 'Index']} />
                    <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                      {dbiData.map((entry) => (
                        <Cell key={entry.model} fill={entry.model === bestModelName ? 'var(--accent)' : 'var(--text-sub)'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="no-data-msg">No Davies-Bouldin data available</p>
              )}
            </div>
          </div>
        </section>

        {/* ── Ranking Section ── */}
        <section className="ranking-section">
          <h2 className="section-title">Model ranking</h2>
          <div className="ranking-list">
            {models.map((model) => (
              <div key={model.model_name} className={model.rank === null ? 'ranking-item rank-na' : `ranking-item rank-${model.rank}`}>
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

        {/* ── Best Model Summary ── */}
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
      </main>
    </div>
  );
}
