import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  PieChart, Pie, Cell,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  LineChart, Line, ResponsiveContainer,
} from 'recharts';
import FutureBehaviorPrediction from './FutureBehaviorPrediction';
import './App.css';

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

const PROFILE_TICKS = [0, 24, 48, 72, 95];
const PROFILE_TICK_LABELS = { 0: '00:00', 24: '06:00', 48: '12:00', 72: '18:00', 95: '23:45' };

function RiskBadge({ risk }) {
  return (
    <span className={`badge badge-risk-${(risk || 'normal').toLowerCase()}`}>
      {risk || '—'}
    </span>
  );
}

function LabelBadge({ label }) {
  const key = label === 'Normal Weekday Demand' ? 'normal'
    : label === 'Peak Demand Day' ? 'peak'
    : label === 'Abnormal Demand Day' ? 'abnormal'
    : 'holiday';
  return <span className={`badge badge-label-${key}`}>{label || '—'}</span>;
}

export default function BehaviorIntelligenceDashboard() {
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
        setDayProfile(res.data.data);
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
        <p>Backend not running. Start with:</p>
        <code>uvicorn app.main:app --reload --port 8001</code>
      </div>
    );
  }

  const recentDays = (dashboardData.all_days || []).slice(-50).reverse();

  const lineColor = selectedDay
    ? (LABEL_COLORS[selectedDay.behavior_label] || '#6366f1')
    : '#6366f1';

  return (
    <div className="app">
      {/* ── Header ── */}
      <header className="app-header">
        <h1>Electricity Demand Behaviour Intelligence</h1>
        <p>Sri Lanka Grid Analysis — AI-Powered Daily Pattern Classification</p>
      </header>

      <main className="app-main">
        {/* ── KPI Cards ── */}
        <section className="kpi-row">
          <div className="kpi-card kpi-blue">
            <span className="kpi-value">{dashboardData.total_days}</span>
            <span className="kpi-label">Total Days Analyzed</span>
          </div>
          <div className="kpi-card kpi-green">
            <span className="kpi-value">{dashboardData.normal_days}</span>
            <span className="kpi-label">Normal Demand Days</span>
          </div>
          <div className="kpi-card kpi-orange">
            <span className="kpi-value">{dashboardData.peak_days}</span>
            <span className="kpi-label">Peak Demand Days</span>
          </div>
          <div className="kpi-card kpi-red">
            <span className="kpi-value">{dashboardData.abnormal_days}</span>
            <span className="kpi-label">Abnormal Days</span>
          </div>
          <div className="kpi-card kpi-lightblue">
            <span className="kpi-value">{dashboardData.holiday_days}</span>
            <span className="kpi-label">Holiday / Low Demand</span>
          </div>
        </section>

        {/* ── Charts Row ── */}
        <section className="charts-row">
          <div className="chart-card">
            <h3 className="chart-title">Behaviour Label Distribution</h3>
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={dashboardData.label_distribution}
                  dataKey="count"
                  nameKey="label"
                  cx="50%"
                  cy="50%"
                  outerRadius={90}
                  label={({ label, percentage }) => `${percentage}%`}
                >
                  {dashboardData.label_distribution.map((entry) => (
                    <Cell
                      key={entry.label}
                      fill={LABEL_COLORS[entry.label] || '#94a3b8'}
                    />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value, name, props) =>
                    [`${value} days (${props.payload.percentage}%)`, props.payload.label]
                  }
                />
                <Legend
                  formatter={(value, entry) => entry.payload.label}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="chart-card">
            <h3 className="chart-title">Risk Level Distribution</h3>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={dashboardData.risk_distribution} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="risk" tick={{ fontSize: 13 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {dashboardData.risk_distribution.map((entry) => (
                    <Cell key={entry.risk} fill={RISK_COLORS[entry.risk] || '#94a3b8'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>

        {/* ── Day Explorer ── */}
        <section className="explorer-section">
          <div className="day-table-panel">
            <h3 className="panel-title">All Days (Recent 50)</h3>
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
                          style={{ background: LABEL_COLORS[day.behavior_label] || '#94a3b8' }}
                        />
                        {day.behavior_label}
                      </td>
                      <td><RiskBadge risk={day.behavior_risk_level} /></td>
                      <td>{day.peak_demand != null ? day.peak_demand.toFixed(1) : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="day-detail-panel">
            <h3 className="panel-title">
              Selected Day — {selectedDay ? selectedDay.date : '—'}
            </h3>
            {selectedDay && (
              <div className="detail-grid">
                <div className="detail-row">
                  <span className="detail-label">Behaviour Label</span>
                  <LabelBadge label={selectedDay.behavior_label} />
                </div>
                <div className="detail-row">
                  <span className="detail-label">Risk Level</span>
                  <RiskBadge risk={selectedDay.behavior_risk_level} />
                </div>
                <div className="detail-row">
                  <span className="detail-label">Peak Demand</span>
                  <span className="detail-value">
                    {selectedDay.peak_demand != null ? `${selectedDay.peak_demand.toFixed(1)} kW` : '—'}
                  </span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Mean Demand</span>
                  <span className="detail-value">
                    {selectedDay.mean_demand != null ? `${selectedDay.mean_demand.toFixed(1)} kW` : '—'}
                  </span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Anomaly Score</span>
                  <span className="detail-value">
                    {selectedDay.isolation_anomaly_score != null
                      ? selectedDay.isolation_anomaly_score.toFixed(4)
                      : '—'}
                  </span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Peak Z-Score</span>
                  <span className="detail-value">
                    {selectedDay.peak_zscore != null ? selectedDay.peak_zscore.toFixed(3) : '—'}
                  </span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">KMeans Cluster</span>
                  <span className="detail-value">{selectedDay.kmeans_cluster ?? '—'}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">DBSCAN Cluster</span>
                  <span className="detail-value">{selectedDay.dbscan_cluster ?? '—'}</span>
                </div>
                {dayProfile && (
                  <div className="detail-row detail-reason">
                    <span className="detail-label">Reason</span>
                    <span className="detail-value reason-text">{dayProfile.behavior_reason || '—'}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </section>

        {/* ── 96-point Day Profile Chart ── */}
        <section className="profile-section">
          <div className="chart-card">
            <h3 className="chart-title">
              Load Profile — {selectedDay ? selectedDay.date : '…'}
            </h3>
            {profileLoading && <div className="profile-loading">Loading profile…</div>}
            {!profileLoading && dayProfile && (
              <ResponsiveContainer width="100%" height={280}>
                <LineChart
                  data={dayProfile.profile_points}
                  margin={{ top: 10, right: 20, left: 10, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis
                    dataKey="slot"
                    type="number"
                    domain={[0, 95]}
                    ticks={PROFILE_TICKS}
                    tickFormatter={(v) => PROFILE_TICK_LABELS[v] || ''}
                    tick={{ fontSize: 12 }}
                  />
                  <YAxis
                    tick={{ fontSize: 12 }}
                    label={{ value: 'Load Demand (kW)', angle: -90, position: 'insideLeft', offset: 10, style: { fontSize: 12 } }}
                  />
                  <Tooltip
                    formatter={(v) => [`${v.toFixed(1)} kW`, 'Load']}
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
          </div>
        </section>

        {/* ── Recent Abnormal Days Table ── */}
        <section className="abnormal-section">
          <h3 className="section-title">Recent Abnormal Days</h3>
          <div className="table-wrapper">
            <table className="data-table striped">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Peak Demand (kW)</th>
                  <th>Mean Demand (kW)</th>
                  <th>Risk</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {(dashboardData.recent_abnormal_days || []).map((day) => (
                  <tr key={day.date}>
                    <td>{day.date}</td>
                    <td>{day.peak_demand != null ? day.peak_demand.toFixed(1) : '—'}</td>
                    <td>{day.mean_demand != null ? day.mean_demand.toFixed(1) : '—'}</td>
                    <td><RiskBadge risk={day.behavior_risk_level} /></td>
                    <td className="reason-cell">{day.behavior_reason || '—'}</td>
                  </tr>
                ))}
                {(!dashboardData.recent_abnormal_days || dashboardData.recent_abnormal_days.length === 0) && (
                  <tr>
                    <td colSpan={5} style={{ textAlign: 'center', color: '#94a3b8' }}>No abnormal days found</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        {/* ── Future Prediction ── */}
        <FutureBehaviorPrediction />
      </main>
    </div>
  );
}
