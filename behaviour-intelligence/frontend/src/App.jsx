import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  PieChart, Pie, Cell,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  LineChart, Line, ReferenceLine, ResponsiveContainer,
} from 'recharts';
import FutureBehaviorPrediction from './FutureBehaviorPrediction.jsx';
import ModelComparison from './ModelComparison.jsx';
import AnomalyComparison from './AnomalyComparison.jsx';
import TuningValidation from './TuningValidation.jsx';
import TeammateComponentView from './TeammateComponentView.jsx';
import OTHER_COMPONENTS from './components.config.js';
import { formatKW, formatScore, formatPercent } from './format.js';
import './App.css';

const BASE_URL = 'http://127.0.0.1:8001';
const MADHUSHANI_LIME_URL = 'http://localhost:5173/anomaly-diagnosis';

// LIME explanation URL for one date (Madushani's focused BI view).
function limeUrlForDate(date) {
  return date
    ? `${MADHUSHANI_LIME_URL}?source=bi&date=${date}`
    : `${MADHUSHANI_LIME_URL}?source=bi`;
}

const LABEL_COLORS = {
  'Normal Demand Day': 'var(--status-normal)',
  'Peak Demand Day': 'var(--status-medium)',
  'Abnormal Demand Day': 'var(--status-high)',
  'Low Demand Day': 'var(--status-low)',
};

const RISK_COLORS = {
  Normal: 'var(--status-normal)',
  Medium: 'var(--status-medium)',
  High: 'var(--status-high)',
  Low: 'var(--status-low)',
};

const PROFILE_TICKS = [0, 24, 48, 72, 95];
const PROFILE_TICK_LABELS = { 0: '00:00', 24: '06:00', 48: '12:00', 72: '18:00', 95: '23:45' };

function monthYear(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
}

function RiskBadge({ risk }) {
  return (
    <span className={`badge badge-risk-${(risk || 'normal').toLowerCase()}`}>
      {risk || '—'}
    </span>
  );
}

function LabelBadge({ label }) {
  const key = label === 'Normal Demand Day' ? 'normal'
    : label === 'Peak Demand Day' ? 'peak'
    : label === 'Abnormal Demand Day' ? 'abnormal'
    : 'low';
  return <span className={`badge badge-label-${key}`}>{label || '—'}</span>;
}

// "0 — Weekday pattern" style name for a K-Means cluster id, from the
// backend's cluster_interpretation (falls back to the bare id).
function clusterName(interpretation, id) {
  if (id === null || id === undefined) return '—';
  const c = interpretation?.clusters?.find((x) => x.cluster === id);
  return c ? `${id} — ${c.name}` : String(id);
}

function DemandRegimes({ interpretation }) {
  if (!interpretation?.clusters?.length) return null;
  return (
    <section className="chart-card regimes-card">
      <h3 className="chart-title">Demand regimes found by clustering (K-Means, k = 2)</h3>
      <div className="regime-grid">
        {interpretation.clusters.map((c) => (
          <div key={c.cluster} className="regime-tile">
            <p className="regime-name">Cluster {c.cluster} = {c.name} <span className="regime-days">({c.days.toLocaleString()} days)</span></p>
            <ul className="regime-facts">
              <li>Weekdays {c.weekday_share_pct}% · weekends {c.weekend_share_pct}%</li>
              <li>Mean demand {c.mean_demand_kw.toLocaleString()} kW · mean daily peak {c.mean_peak_kw.toLocaleString()} kW</li>
              <li>Profile peak at {c.peak_time}, lowest at {c.trough_time}</li>
              {c.minority_day_type_days > 0 && (
                <li>
                  {c.minority_day_type_days} {c.weekend_share_pct >= 50 ? 'weekday' : 'weekend'} days in this
                  cluster, {c.minority_day_type_anomalies} of them anomaly days
                </li>
              )}
            </ul>
          </div>
        ))}
      </div>
      <p className="regime-note">{interpretation.role_note}</p>
    </section>
  );
}

function AnomalyDot(props) {
  const { cx, cy, payload } = props;
  if (!payload.isAbnormal) return null;
  return <circle key={payload.date} cx={cx} cy={cy} r={4} fill="var(--status-high)" stroke="var(--text)" strokeWidth={1} />;
}

export default function BehaviorIntelligenceDashboard() {
  const [currentView, setCurrentView] = useState('dashboard');
  // When set, the Explainable AI view opens this LIME deep link instead of
  // the XAI home page (LIME buttons open the explanation inside BI).
  const [xaiDeepLink, setXaiDeepLink] = useState(null);

  const openLimeForDate = (date) => {
    setXaiDeepLink(limeUrlForDate(date));
    setCurrentView('xai');
  };
  const showView = (view) => {
    setXaiDeepLink(null);
    setCurrentView(view);
  };
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedDay, setSelectedDay] = useState(null);
  const [dayProfile, setDayProfile] = useState(null);
  const [profileLoading, setProfileLoading] = useState(false);

  useEffect(() => {
    axios
      .get(`${BASE_URL}/api/dashboard-summary`)
      .then((res) => {
        const data = res.data.data;
        setDashboardData(data);
        if (data.all_days && data.all_days.length > 0) {
          setSelectedDay(data.all_days[data.all_days.length - 1]);
        }
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (!selectedDay) return;
    setProfileLoading(true);
    setDayProfile(null);
    axios
      .get(`${BASE_URL}/api/get-day-profile?date=${selectedDay.date}`)
      .then((res) => {
        if (res.data.success && res.data.data && res.data.data.profile_points) {
          setDayProfile(res.data.data);
        } else {
          setDayProfile(null);
        }
        setProfileLoading(false);
      })
      .catch(() => setProfileLoading(false));
  }, [selectedDay]);

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner" />
        <p>Loading dashboard…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-screen">
        <h2>Cannot connect to backend</h2>
        <p>Start the backend first:</p>
        <code>python -m uvicorn app.main:app --port 8001</code>
      </div>
    );
  }

  // Render different views based on currentView
  const renderMainContent = () => {
    if (currentView === 'comparison') {
      return <ModelComparison />;
    }
    if (currentView === 'anomaly-comparison') {
      return <AnomalyComparison />;
    }
    if (currentView === 'tuning') {
      return <TuningValidation />;
    }
    const teammate = OTHER_COMPONENTS.find((c) => c.key === currentView);
    if (teammate) {
      const deepLink = teammate.key === 'xai' ? xaiDeepLink : null;
      return (
        <TeammateComponentView
          key={deepLink || teammate.key}
          component={teammate}
          url={deepLink || undefined}
          onBack={deepLink ? () => showView('dashboard') : undefined}
        />
      );
    }
    // Default dashboard view
    return (
      <div className="app">
        {/* ── Header ── */}
        <header className="app-header">
          <div className="app-header-inner">
            <div className="app-header-brand">
              <h1 className="app-header-title">Daily Demand Behaviour Analysis</h1>
              <p className="app-header-sub">
                Sri Lanka Electricity Grid{dateRangeLabel ? ` · ${dateRangeLabel}` : ''}
              </p>
            </div>
            <div className="header-actions">
              <a className="btn-quick" href={`${BASE_URL}/api/download-report?label=${encodeURIComponent('Abnormal Demand Day')}`}>
                Abnormal days only
              </a>
              <a className="btn-lime" href={`${BASE_URL}/api/download-report`}>
                Download report
              </a>
            </div>
          </div>
        </header>

        <main className="app-main">
        {/* ── KPI Cards ── */}
        <section className="kpi-row">
          <div className="kpi-card kpi-total">
            <span className="kpi-value">{dashboardData.total_days}</span>
            <span className="kpi-label">Total days analyzed</span>
          </div>
          <div className="kpi-card kpi-normal">
            <span className="kpi-value">{dashboardData.normal_days}</span>
            <span className="kpi-label">Normal demand days</span>
            <span className="kpi-pct">{formatPercent(dashboardData.normal_days / dashboardData.total_days * 100)} of total</span>
          </div>
          <div className="kpi-card kpi-medium">
            <span className="kpi-value">{dashboardData.peak_days}</span>
            <span className="kpi-label">Peak demand days</span>
            <span className="kpi-pct">{formatPercent(dashboardData.peak_days / dashboardData.total_days * 100)} of total</span>
          </div>
          <div className="kpi-card kpi-high">
            <span className="kpi-value">{dashboardData.abnormal_days}</span>
            <span className="kpi-label">Abnormal days</span>
            <span className="kpi-pct">{formatPercent(dashboardData.abnormal_days / dashboardData.total_days * 100)} of total</span>
          </div>
          <div className="kpi-card kpi-high">
            <span className="kpi-value">{dashboardData.detected_anomaly_days}</span>
            <span className="kpi-label">Detected anomalies (Isolation Forest)</span>
            <span className="kpi-pct">
              {dashboardData.abnormal_days} Abnormal + {dashboardData.anomaly_days_labelled_peak} Peak
            </span>
          </div>
          <div className="kpi-card kpi-low">
            <span className="kpi-value">{dashboardData.low_days}</span>
            <span className="kpi-label">Low demand days</span>
            <span className="kpi-pct">{formatPercent(dashboardData.low_days / dashboardData.total_days * 100)} of total</span>
          </div>
        </section>
        <p className="kpi-note">{dashboardData.anomaly_label_note}</p>

        <DemandRegimes interpretation={dashboardData.cluster_interpretation} />

        {/* ── Label & Risk Charts ── */}
        <section className="charts-row">
          <div className="chart-card">
            <h3 className="chart-title">Behaviour label distribution</h3>
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={dashboardData.label_distribution}
                  dataKey="count"
                  nameKey="label"
                  cx="50%"
                  cy="50%"
                  outerRadius={90}
                  label={({ percentage }) => formatPercent(percentage)}
                >
                  {dashboardData.label_distribution.map((entry) => (
                    <Cell key={entry.label} fill={LABEL_COLORS[entry.label] || 'var(--text-sub)'} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value, name, props) =>
                    [`${value} days (${formatPercent(props.payload.percentage)})`, props.payload.label]
                  }
                />
                <Legend formatter={(value, entry) => entry.payload.label} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="chart-card">
            <h3 className="chart-title">Risk level distribution</h3>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={dashboardData.risk_distribution} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="risk" tick={{ fontSize: 12, fill: 'var(--text-sub)' }} />
                <YAxis tick={{ fontSize: 12, fill: 'var(--text-sub)' }} />
                <Tooltip />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {dashboardData.risk_distribution.map((entry) => (
                    <Cell key={entry.risk} fill={RISK_COLORS[entry.risk] || 'var(--text-sub)'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>

        {/* ── Anomaly Detection Analysis ── */}
        <section className="charts-row">
          <div className="chart-card">
            <h3 className="chart-title">Top 15 anomalous days</h3>
            {topAnomalyDays.length === 0 ? (
              <p className="no-data-msg">No anomaly data available.</p>
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart
                  data={topAnomalyDays}
                  margin={{ top: 10, right: 20, left: 10, bottom: 50 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 10, fill: 'var(--text-sub)' }}
                    angle={-40}
                    textAnchor="end"
                    interval={0}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: 'var(--text-sub)' }}
                    label={{ value: 'Anomaly score', angle: -90, position: 'insideLeft', offset: 5, style: { fontSize: 11, fill: 'var(--text-sub)' } }}
                  />
                  <Tooltip
                    formatter={(v, name, props) => [
                      formatScore(v),
                      `Score (${props.payload.behavior_label})`,
                    ]}
                  />
                  <Bar dataKey="score" radius={[3, 3, 0, 0]}>
                    {topAnomalyDays.map((entry) => (
                      <Cell
                        key={entry.date}
                        fill={entry.behavior_label === 'Abnormal Demand Day' ? 'var(--status-high)' : 'var(--status-medium)'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="chart-card">
            <h3 className="chart-title">Anomaly score trend — last 180 days</h3>
            {anomalyTrend.length === 0 ? (
              <p className="no-data-msg">No trend data available.</p>
            ) : (
              <>
                <p className="chart-legend-note">
                  <span className="legend-dot" style={{ background: 'var(--status-high)' }} /> Marked points = Abnormal demand days
                </p>
                <ResponsiveContainer width="100%" height={240}>
                  <LineChart
                    data={anomalyTrend}
                    margin={{ top: 10, right: 20, left: 10, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis dataKey="date" tick={false} />
                    <YAxis
                      tick={{ fontSize: 11, fill: 'var(--text-sub)' }}
                      label={{ value: 'Anomaly score', angle: -90, position: 'insideLeft', offset: 5, style: { fontSize: 11, fill: 'var(--text-sub)' } }}
                    />
                    <Tooltip
                      formatter={(v) => [formatScore(v), 'Anomaly score']}
                      labelFormatter={(label) => `Date: ${label}`}
                    />
                    <ReferenceLine y={0} stroke="var(--border)" strokeDasharray="4 4" label={{ value: 'Threshold (0)', position: 'insideTopRight', fontSize: 10, fill: 'var(--text-dim)' }} />
                    <Line
                      type="monotone"
                      dataKey="score"
                      stroke="var(--accent)"
                      strokeWidth={1.5}
                      dot={<AnomalyDot />}
                      activeDot={{ r: 4 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </>
            )}
          </div>
        </section>

        {/* ── Day Explorer ── */}
        <section className="explorer-section">
          <div className="day-table-panel">
            <h3 className="panel-title">All days — recent 50</h3>
            <div className="day-table-scroll">
              <table className="day-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Label</th>
                    <th>Risk</th>
                    <th>Peak kW</th>
                  </tr>
                </thead>
                <tbody>
                  {recentDays.map((day) => (
                    <tr
                      key={day.date}
                      className={selectedDay && selectedDay.date === day.date ? 'row-selected' : ''}
                      onClick={() => setSelectedDay(day)}
                    >
                      <td>{day.date}</td>
                      <td>
                        <span
                          className="dot"
                          style={{ background: LABEL_COLORS[day.behavior_label] || 'var(--text-sub)' }}
                        />
                        {day.behavior_label}
                      </td>
                      <td><RiskBadge risk={day.behavior_risk_level} /></td>
                      <td>{formatKW(day.peak_demand)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="day-detail-panel">
            <h3 className="panel-title">
              Selected day — {selectedDay ? selectedDay.date : '—'}
            </h3>
            {selectedDay && (
              <div className="detail-grid">
                <div className="detail-row">
                  <span className="detail-label">Behaviour label</span>
                  <LabelBadge label={selectedDay.behavior_label} />
                </div>
                <div className="detail-row">
                  <span className="detail-label">Risk level</span>
                  <RiskBadge risk={selectedDay.behavior_risk_level} />
                </div>
                <div className="detail-row">
                  <span className="detail-label">Peak demand</span>
                  <span className="detail-value">
                    {selectedDay.peak_demand != null ? `${formatKW(selectedDay.peak_demand)} kW` : '—'}
                  </span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Mean demand</span>
                  <span className="detail-value">
                    {selectedDay.mean_demand != null ? `${formatKW(selectedDay.mean_demand)} kW` : '—'}
                  </span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Anomaly score</span>
                  <span className="detail-value">
                    {formatScore(selectedDay.isolation_anomaly_score)}
                  </span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Peak z-score (signed)</span>
                  <span className="detail-value">
                    {formatScore(selectedDay.peak_zscore_signed ?? selectedDay.peak_zscore)}
                  </span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">K-Means cluster</span>
                  <span className="detail-value">
                    {clusterName(dashboardData.cluster_interpretation, selectedDay.kmeans_cluster)}
                  </span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">DBSCAN cluster</span>
                  <span className="detail-value">{selectedDay.dbscan_cluster ?? '—'}</span>
                </div>
                {dayProfile && dayProfile.behavior_reason && (
                  <div className="detail-row detail-reason">
                    <span className="detail-label">Reason</span>
                    <span className="detail-value reason-text">{dayProfile.behavior_reason}</span>
                  </div>
                )}
              </div>
            )}

            {selectedDay && selectedDay.behavior_label === 'Abnormal Demand Day' && (
              <div className="lime-detail-action">
                <span className="lime-detail-hint">
                  Anomaly detected — view feature importance in the XAI component
                </span>
                <button
                  className="btn-lime"
                  onClick={() => openLimeForDate(selectedDay.date)}
                >
                  Show LIME explanation →
                </button>
              </div>
            )}
          </div>
        </section>

        {/* ── 96-point Day Profile Chart ── */}
        <section className="profile-section">
          <div className="chart-card">
            <h3 className="chart-title">
              Load profile (96 × 15-min slots) — {selectedDay ? selectedDay.date : '…'}
            </h3>
            {profileLoading && <div className="profile-loading">Loading profile…</div>}

            {!profileLoading && dayProfile && dayProfile.profile_points && dayProfile.profile_points.length > 0 && (
              <ResponsiveContainer width="100%" height={280}>
                <LineChart
                  data={dayProfile.profile_points}
                  margin={{ top: 10, right: 20, left: 10, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis
                    dataKey="slot"
                    type="number"
                    domain={[0, 95]}
                    ticks={PROFILE_TICKS}
                    tickFormatter={(v) => PROFILE_TICK_LABELS[v] || ''}
                    tick={{ fontSize: 12, fill: 'var(--text-sub)' }}
                  />
                  <YAxis
                    tick={{ fontSize: 12, fill: 'var(--text-sub)' }}
                    label={{ value: 'Load demand (kW)', angle: -90, position: 'insideLeft', offset: 10, style: { fontSize: 12, fill: 'var(--text-sub)' } }}
                  />
                  <Tooltip
                    formatter={(v) => [`${formatKW(v)} kW`, 'Load']}
                    labelFormatter={(slot) => {
                      const h = Math.floor(slot / 4);
                      const m = (slot % 4) * 15;
                      return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke={lineColor}
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}

            {!profileLoading && !dayProfile && (
              <p className="no-data-msg">No load profile available for this date.</p>
            )}
          </div>
        </section>

        {/* ── Recent Abnormal Days Table ── */}
        <section className="abnormal-section">
          <h3 className="section-title">Recent abnormal days</h3>
          <div className="table-wrapper">
            <table className="data-table striped">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Peak demand (kW)</th>
                  <th>Mean demand (kW)</th>
                  <th>Anomaly score</th>
                  <th>Risk</th>
                  <th>Reason</th>
                  <th>XAI</th>
                </tr>
              </thead>
              <tbody>
                {(dashboardData.recent_abnormal_days || []).map((day) => (
                  <tr key={day.date}>
                    <td>{day.date}</td>
                    <td>{formatKW(day.peak_demand)}</td>
                    <td>{formatKW(day.mean_demand)}</td>
                    <td>{formatScore(day.isolation_anomaly_score)}</td>
                    <td><RiskBadge risk={day.behavior_risk_level} /></td>
                    <td className="reason-cell">{day.behavior_reason || '—'}</td>
                    <td>
                      <button
                        className="btn-lime-sm"
                        onClick={() => openLimeForDate(day.date)}
                        title="View LIME explanation for this anomaly"
                      >
                        LIME →
                      </button>
                    </td>
                  </tr>
                ))}
                {(!dashboardData.recent_abnormal_days || dashboardData.recent_abnormal_days.length === 0) && (
                  <tr>
                    <td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-dim)' }}>No abnormal days found</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        {/* ── Future Prediction ── */}
        <FutureBehaviorPrediction
          recentAbnormalDays={dashboardData.recent_abnormal_days || []}
          onOpenLime={openLimeForDate}
        />
        </main>
      </div>
    );
  };

  const recentDays = (dashboardData.all_days || []).slice(-50).reverse();

  const lineColor = selectedDay
    ? (LABEL_COLORS[selectedDay.behavior_label] || 'var(--accent)')
    : 'var(--accent)';

  const topAnomalyDays = (dashboardData.all_days || [])
    .filter(d => d.isolation_anomaly_score != null && d.isolation_anomaly_score > 0)
    .sort((a, b) => b.isolation_anomaly_score - a.isolation_anomaly_score)
    .slice(0, 15)
    .map(d => ({
      date: d.date,
      score: parseFloat(d.isolation_anomaly_score.toFixed(4)),
      behavior_label: d.behavior_label,
    }));

  const anomalyTrend = (dashboardData.all_days || [])
    .slice(-180)
    .map(d => ({
      date: d.date,
      score: d.isolation_anomaly_score != null ? parseFloat(d.isolation_anomaly_score.toFixed(4)) : 0,
      isAbnormal: d.behavior_label === 'Abnormal Demand Day',
    }));

  const allDays = dashboardData.all_days || [];
  const dateRangeLabel = allDays.length > 0
    ? `${monthYear(allDays[0].date)} – ${monthYear(allDays[allDays.length - 1].date)}`
    : null;

  return (
    <div className="shell">
      {/* ── Sidebar ── */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="sidebar-brand-title">Electricity Demand Intelligence System</span>
        </div>

        <nav className="sidebar-nav">
          <div className="sidebar-group">
            <span className="sidebar-group-label">Behaviour Intelligence</span>
            <button
              className={`sidebar-item ${currentView === 'dashboard' ? 'sidebar-item-active' : ''}`}
              onClick={() => showView('dashboard')}
            >
              Dashboard
            </button>
            <button
              className={`sidebar-item ${currentView === 'comparison' ? 'sidebar-item-active' : ''}`}
              onClick={() => showView('comparison')}
            >
              Model Comparison
            </button>
            <button
              className={`sidebar-item ${currentView === 'anomaly-comparison' ? 'sidebar-item-active' : ''}`}
              onClick={() => showView('anomaly-comparison')}
            >
              Anomaly Comparison
            </button>
            <button
              className={`sidebar-item ${currentView === 'tuning' ? 'sidebar-item-active' : ''}`}
              onClick={() => showView('tuning')}
            >
              Tuning &amp; Validation
            </button>
          </div>

          <div className="sidebar-group">
            <span className="sidebar-group-label">Other Components</span>
            {OTHER_COMPONENTS.map((c) => (
              <button
                key={c.key}
                className={`sidebar-item ${currentView === c.key ? 'sidebar-item-active' : ''}`}
                onClick={() => showView(c.key)}
              >
                {c.name}
              </button>
            ))}
          </div>
        </nav>
      </aside>

      {/* ── Content ── */}
      <div className="shell-content">
        {renderMainContent()}
      </div>
    </div>
  );
}
