import { BrowserRouter, Routes, Route, NavLink, Navigate, useLocation } from 'react-router-dom'
import { TrendingUp, AlertTriangle, Scale } from 'lucide-react'
import TemporalDrift from './pages/TemporalDrift'
import LimeAnomalyDiagnosis from './pages/LimeAnomalyDiagnosis'
import ModelXaiComparison from './pages/ModelXaiComparison'
import './App.css'

const navItems = [
  { path: '/temporal-drift',       label: 'SHAP Temporal Drift',    number: '01', Icon: TrendingUp,    ready: true },
  { path: '/anomaly-diagnosis',    label: 'LIME Anomaly Diagnosis', number: '02', Icon: AlertTriangle, ready: true },
  { path: '/model-xai-comparison', label: 'Model & XAI Comparison', number: '03', Icon: Scale,         ready: true },
]

function Layout() {
  const location = useLocation()
  // Arriving from Thanujan's dashboard for one specific anomaly: show only
  // that explanation, full width, no sidebar/nav — the page has its own
  // "Back to Dashboard" button for this case.
  const isFocusedBIView =
    location.pathname === '/anomaly-diagnosis' &&
    new URLSearchParams(location.search).get('source') === 'bi'

  if (isFocusedBIView) {
    return (
      <main className="main main--focused">
        <LimeAnomalyDiagnosis />
      </main>
    )
  }

  return (
    <div className="layout">

      <aside className="sidebar">
        <div className="nav-group">
          <p className="nav-group-label">XAI Components</p>
          <nav className="nav">
            {navItems.map(({ path, label, number, Icon, ready }) =>
              ready ? (
                <NavLink
                  key={path}
                  to={path}
                  className={({ isActive }) =>
                    `nav-item ${isActive ? 'nav-item--active' : ''}`
                  }
                >
                  <Icon className="nav-icon" size={15} />
                  <span className="nav-number">{number}</span>
                  <span className="nav-label">{label}</span>
                  <span className="nav-status-dot" />
                </NavLink>
              ) : (
                <div key={path} className="nav-item nav-item--disabled">
                  <Icon className="nav-icon" size={15} />
                  <span className="nav-number">{number}</span>
                  <span className="nav-label">{label}</span>
                  <span className="nav-badge">Soon</span>
                </div>
              )
            )}
          </nav>
        </div>

        <div className="sidebar-footer">
          <p className="sidebar-footer-label">Project</p>
          <p className="sidebar-footer-text">
            AI-Based Electricity Demand<br />
            Intelligence System  R26-IT-010<br />
            SLIIT · 2026
          </p>
        </div>
      </aside>

      <main className="main">
        <Routes>
          <Route path="/" element={<Navigate to="/temporal-drift" replace />} />
          <Route path="/temporal-drift"    element={<TemporalDrift />} />
          <Route path="/anomaly-diagnosis" element={<LimeAnomalyDiagnosis />} />
          <Route path="/model-xai-comparison" element={<ModelXaiComparison />} />
        </Routes>
      </main>

    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/*" element={<Layout />} />
      </Routes>
    </BrowserRouter>
  )
}

