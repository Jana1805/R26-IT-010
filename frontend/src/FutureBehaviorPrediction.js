import React, { useState } from 'react';
import axios from 'axios';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts';

const BASE_URL = 'http://127.0.0.1:8001';

const LABEL_COLORS = {
  'Normal Weekday Demand': '#22c55e',
  'Peak Demand Day': '#f97316',
  'Abnormal Demand Day': '#ef4444',
  'Holiday / Low Demand Day': '#3b82f6',
};

const RISK_COLORS = {
  Normal: '#22c55e',
  Medium: '#f97316',
  High: '#ef4444',
  Low: '#3b82f6',
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
      <h3 className="section-title">Future Behavior Prediction</h3>

      <div className="prediction-controls">
        <div className="date-input-group">
          <label htmlFor="pred-date">Select Date</label>
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
              <span className="pred-meta">Predicted Behaviour</span>
              <span className={`badge badge-label-${labelKey} badge-lg`}>
                {result.predicted_label}
              </span>
            </div>
            <div className="pred-main">
              <span className="pred-meta">Confidence</span>
              <span className="pred-confidence">{result.confidence_percent}%</span>
            </div>
            <div className="pred-main">
              <span className="pred-meta">Risk Level</span>
              <span
                className="badge badge-lg"
                style={{
                  background: RISK_COLORS[result.risk_level] || '#94a3b8',
                  color: '#fff',
                }}
              >
                {result.risk_level}
              </span>
            </div>
            <div className="pred-main">
              <span className="pred-meta">Matched Days</span>
              <span className="pred-stat">{result.matched_days_count}</span>
            </div>
            <div className="pred-main">
              <span className="pred-meta">Match Strategy</span>
              <span className="pred-stat">{result.match_strategy}</span>
            </div>
          </div>

          <p className="pred-explanation">{result.explanation}</p>

          {/* ── Anomaly Alert + LIME button ── */}
          {result.predicted_label === 'Abnormal Demand Day' && (
            <div className="anomaly-alert">
              <div className="anomaly-alert-header">
                <span className="anomaly-alert-icon">⚠</span>
                Anomaly Detected — Explainable AI Analysis Available
              </div>
              <div className="anomaly-alert-body">
                <p className="anomaly-alert-text">
                  This date is predicted to show abnormal electricity demand behaviour.
                  Use LIME (Local Interpretable Model-agnostic Explanations) to understand
                  which features are driving this anomaly.
                </p>
                <div className="anomaly-confidence-row">
                  <span className="anomaly-confidence-label">Model Confidence</span>
                  <span className="anomaly-confidence-value">{result.confidence_percent}%</span>
                </div>
              </div>
              <div>
                <button className="btn-lime" onClick={() => openLimeExplainer(selectedDate)}>
                  Show LIME Explanation →
                </button>
              </div>
            </div>
          )}

          {/* ── Similar Past Anomalies ── */}
          {result.predicted_label === 'Abnormal Demand Day' && recentAbnormalDays.length > 0 && (
            <div className="similar-anomalies">
              <p className="similar-anomalies-title">Similar Past Anomalies (for reference)</p>
              <div className="table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Peak Demand (kW)</th>
                      <th>Anomaly Score</th>
                      <th>Risk</th>
                      <th>Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentAbnormalDays.slice(0, 5).map((day) => (
                      <tr key={day.date}>
                        <td>{day.date}</td>
                        <td>{day.peak_demand != null ? day.peak_demand.toFixed(1) : '—'}</td>
                        <td>{day.isolation_anomaly_score != null ? day.isolation_anomaly_score.toFixed(4) : '—'}</td>
                        <td><RiskBadge risk={day.behavior_risk_level} /></td>
                        <td style={{ fontSize: '0.78rem', color: '#64748b', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
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
            <h4 className="chart-subtitle">Probability Distribution</h4>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={probData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="label" tick={{ fontSize: 12 }} />
                <YAxis domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 12 }} />
                <Tooltip formatter={(v) => [`${v}%`, 'Probability']} />
                <Bar dataKey="percentage" radius={[4, 4, 0, 0]}>
                  {probData.map((entry) => (
                    <Cell
                      key={entry.fullLabel}
                      fill={LABEL_COLORS[entry.fullLabel] || '#94a3b8'}
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
