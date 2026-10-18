import React, { useState } from 'react';
import axios from 'axios';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts';
import { formatKW, formatScore, formatPercent } from './format.js';

const BASE_URL = 'http://127.0.0.1:8001';

const LABEL_COLORS = {
  'Normal Weekday Demand': 'var(--status-normal)',
  'Peak Demand Day': 'var(--status-medium)',
  'Abnormal Demand Day': 'var(--status-high)',
  'Holiday / Low Demand Day': 'var(--status-low)',
};

const MADHUSHANI_LIME_URL = 'http://localhost:5173/anomaly-diagnosis';

function RiskBadge({ risk }) {
  return (
    <span className={`badge badge-risk-${(risk || 'normal').toLowerCase()}`}>
      {risk || '—'}
    </span>
  );
}

function openLimeExplainer(date) {
  const url = date
    ? `${MADHUSHANI_LIME_URL}?source=bi&date=${date}`
    : `${MADHUSHANI_LIME_URL}?source=bi`;
  window.open(url, '_blank', 'noopener,noreferrer');
}

const SHORT_LABELS = {
  'Normal Weekday Demand': 'Normal',
  'Peak Demand Day': 'Peak',
  'Abnormal Demand Day': 'Abnormal',
  'Holiday / Low Demand Day': 'Holiday',
};

function todayStr() {
  return new Date().toISOString().split('T')[0];
}

function addDays(n) {
  const d = new Date();
  d.setDate(d.getDate() + n);
  return d.toISOString().split('T')[0];
}

function nextWeekday(dayOfWeek) {
  const d = new Date();
  const diff = (dayOfWeek - d.getDay() + 7) % 7 || 7;
  d.setDate(d.getDate() + diff);
  return d.toISOString().split('T')[0];
}

export default function FutureBehaviorPrediction({ recentAbnormalDays = [] }) {
  const [selectedDate, setSelectedDate] = useState(todayStr());
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  function handlePredict() {
    setLoading(true);
    setError(null);
    setResult(null);
    axios
      .get(`${BASE_URL}/api/predict-future-behavior?date=${selectedDate}`)
      .then((res) => {
        setResult(res.data.data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.response?.data?.message || 'Prediction failed. Is the backend running?');
        setLoading(false);
      });
  }

  const probData = result
    ? Object.entries(result.probability_distribution).map(([label, pct]) => ({
        label: SHORT_LABELS[label] || label,
        fullLabel: label,
        percentage: pct,
      }))
    : [];

  const labelKey = result?.predicted_label === 'Normal Weekday Demand' ? 'normal'
    : result?.predicted_label === 'Peak Demand Day' ? 'peak'
    : result?.predicted_label === 'Abnormal Demand Day' ? 'abnormal'
    : 'holiday';

  return (
    <section className="prediction-section">
      <h3 className="section-title">Future behaviour prediction</h3>

      <div className="prediction-controls">
        <div className="date-input-group">
          <label htmlFor="pred-date">Select date</label>
          <input
            id="pred-date"
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="date-input"
          />
        </div>

        <div className="quick-buttons">
          <button className="btn-quick" onClick={() => setSelectedDate(addDays(1))}>
            Tomorrow
          </button>
          <button className="btn-quick" onClick={() => setSelectedDate(nextWeekday(1))}>
            Next Monday
          </button>
          <button className="btn-quick" onClick={() => setSelectedDate(nextWeekday(5))}>
            Next Friday
          </button>
        </div>

        <button
          className="btn-predict"
          onClick={handlePredict}
          disabled={loading || !selectedDate}
        >
          {loading ? 'Predicting…' : 'Predict'}
        </button>
      </div>

      {error && <div className="pred-error">{error}</div>}

      {result && (
        <div className="prediction-result">
          <div className="pred-top-row">
            <div className="pred-main">
              <span className="pred-meta">Predicted behaviour</span>
              <span className={`badge badge-label-${labelKey} badge-lg`}>
                {result.predicted_label}
              </span>
            </div>
            <div className="pred-main">
              <span className="pred-meta">Confidence</span>
              <span className="pred-confidence">{formatPercent(result.confidence_percent)}</span>
            </div>
            <div className="pred-main">
              <span className="pred-meta">Risk level</span>
              <RiskBadge risk={result.risk_level} />
            </div>
            <div className="pred-main">
              <span className="pred-meta">Matched days</span>
              <span className="pred-stat">{result.matched_days_count}</span>
            </div>
            <div className="pred-main">
              <span className="pred-meta">Match strategy</span>
              <span className="pred-stat">{result.match_strategy}</span>
            </div>
          </div>

          <p className="pred-explanation">{result.explanation}</p>

          {/* ── Anomaly Alert + LIME button ── */}
          {result.predicted_label === 'Abnormal Demand Day' && (
            <div className="anomaly-alert">
              <div className="anomaly-alert-header">
                <span className="anomaly-alert-icon">⚠</span>
                Anomaly detected — explainable AI analysis available
              </div>
              <div className="anomaly-alert-body">
                <p className="anomaly-alert-text">
                  This date is predicted to show abnormal electricity demand behaviour.
                  Use LIME (Local Interpretable Model-agnostic Explanations) to understand
                  which features are driving this anomaly.
                </p>
                <div className="anomaly-confidence-row">
                  <span className="anomaly-confidence-label">Model confidence</span>
                  <span className="anomaly-confidence-value">{formatPercent(result.confidence_percent)}</span>
                </div>
              </div>
              <div>
                <button className="btn-lime" onClick={() => openLimeExplainer(selectedDate)}>
                  Show LIME explanation →
                </button>
              </div>
            </div>
          )}

          {/* ── Similar Past Anomalies ── */}
          {result.predicted_label === 'Abnormal Demand Day' && recentAbnormalDays.length > 0 && (
            <div className="similar-anomalies">
              <p className="similar-anomalies-title">Similar past anomalies (reference)</p>
              <div className="table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Peak demand (kW)</th>
                      <th>Anomaly score</th>
                      <th>Risk</th>
                      <th>Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentAbnormalDays.slice(0, 5).map((day) => (
                      <tr key={day.date}>
                        <td>{day.date}</td>
                        <td>{formatKW(day.peak_demand)}</td>
                        <td>{formatScore(day.isolation_anomaly_score)}</td>
                        <td><RiskBadge risk={day.behavior_risk_level} /></td>
                        <td className="reason-cell">
                          {day.behavior_reason || '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div className="pred-chart">
            <h4 className="chart-subtitle">Probability distribution</h4>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={probData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="label" tick={{ fontSize: 12, fill: 'var(--text-sub)' }} />
                <YAxis domain={[0, 100]} tickFormatter={(v) => formatPercent(v, 0)} tick={{ fontSize: 12, fill: 'var(--text-sub)' }} />
                <Tooltip formatter={(v) => [formatPercent(v), 'Probability']} />
                <Bar dataKey="percentage" radius={[4, 4, 0, 0]}>
                  {probData.map((entry) => (
                    <Cell
                      key={entry.fullLabel}
                      fill={LABEL_COLORS[entry.fullLabel] || 'var(--text-sub)'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </section>
  );
}
