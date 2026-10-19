import React, { useState, useEffect } from 'react';
import axios from 'axios';
import GridLab from '../gridlab/GridLab.jsx';
import PerformancePanel from '../components/PerformancePanel.jsx';

const API_BASE = ''; // requests go to /api/... and vite proxy forwards to backend

// Friendly display names for the raw Python class names stored in metadata
const FRIENDLY_MODEL_NAME = {
  RandomForestRegressor: 'Random Forest',
  GradientBoostingRegressor: 'Gradient Boosting',
  LinearRegression: 'Linear Regression',
  StackingRegressor: 'Stacking Ensemble',
};
const friendlyModelList = (names) => names?.map(n => FRIENDLY_MODEL_NAME[n] ?? n).join(', ');

// ---------------------------------------------------------------------------
// Scenario definitions: what modifications each scenario applies to baseline
// ---------------------------------------------------------------------------
const SCENARIOS = [
  {
    key: 'heat_wave',
    label: 'Heat Wave',
    description: 'Temperature +8°C, Humidity -15%',
    modify: (b) => ({ ...b, Temperature: b.Temperature + 8, Humidity: Math.max(0, b.Humidity - 15) }),
  },
  {
    key: 'cold_spell',
    label: 'Cold Spell',
    description: 'Temperature -10°C, Humidity +20%',
    modify: (b) => ({ ...b, Temperature: b.Temperature - 10, Humidity: Math.min(100, b.Humidity + 20) }),
  },
  {
    key: 'price_shock',
    label: 'Price Shock',
    description: 'Electricity price doubled',
    modify: (b) => ({ ...b, ElectricityPrice: b.ElectricityPrice * 2 }),
  },
  {
    key: 'economic_boom',
    label: 'Economic Boom',
    description: 'GDP +20%, Per Capita Energy Use +10%',
    modify: (b) => ({ ...b, GDP: b.GDP * 1.2, PerCapitaEnergyUse: b.PerCapitaEnergyUse * 1.1 }),
  },
];

// The form/scenario logic above works with short internal keys (Temperature,
// WindSpeed, ...), but /api/predict reads columns by the real feature names
// from model_metadata.json (e.g. "Temperature (°C)"). Sending the short keys
// directly meant every one of these columns was always missing from the
// request, so the backend silently filled every feature with 0 (see
// backend/app.py predict_demand: `if feature not in df.columns: df[feature]
// = 0`) — every prediction from this UI was computed on all-zero input,
// regardless of what was actually typed into the form.
const API_FEATURE_KEYS = {
  Temperature: 'Temperature (°C)',
  Humidity: 'Humidity (%)',
  WindSpeed: 'Wind Speed (m/s)',
  Rainfall: 'Rainfall (mm)',
  SolarIrradiance: 'Solar Irradiance (W/m²)',
  GDP: 'GDP (LKR)',
  PerCapitaEnergyUse: 'Per Capita Energy Use (kWh)',
  ElectricityPrice: 'Electricity Price (LKR/kWh)',
  DayOfWeek: 'Day of Week',
  HourOfDay: 'Hour of Day',
  Month: 'Month',
  PublicEvent: 'Public Event',
};

// price_shock/economic_boom genuinely produce values like -2e-11 (the model
// measured ~0% importance for price/GDP, see Feature Importance), which
// rounds to a "-0.0" display, a stray minus sign in front of nothing. Snap
// anything that rounds to zero at the given precision to a clean positive 0.
function roundClean(value, decimals) {
  const factor = 10 ** decimals;
  const rounded = Math.round(value * factor) / factor;
  return rounded === 0 ? 0 : rounded;
}

function toApiPayload(form) {
  const payload = {};
  for (const [shortKey, apiKey] of Object.entries(API_FEATURE_KEYS)) {
    payload[apiKey] = form[shortKey];
  }
  return payload;
}

// ---------------------------------------------------------------------------
// Root component
// ---------------------------------------------------------------------------
export default function ProfessionalDashboard() {
  const [modelInfo,   setModelInfo]   = useState(null);
  const [staticScenarios, setStaticScenarios] = useState(null);
  const [prediction,  setPrediction]  = useState(null);
  const [loading,     setLoading]     = useState(true);
  const [error,       setError]       = useState(null);
  const [activeTab,   setActiveTab]   = useState('predict');

  // Live scenario state
  const [liveResults,  setLiveResults]  = useState(null);
  const [liveLoading,  setLiveLoading]  = useState(false);
  const [liveError,    setLiveError]    = useState(null);
  const [baselineForm, setBaselineForm] = useState({
    Temperature: 28, Humidity: 80, WindSpeed: 2, Rainfall: 5,
    SolarIrradiance: 250, GDP: 1000, PerCapitaEnergyUse: 500,
    ElectricityPrice: 25, HourOfDay: 14, Month: 6, DayOfWeek: 2, PublicEvent: 0,
  });

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const modelResponse = await axios.get(`${API_BASE}/api/model-info`);
      setModelInfo(modelResponse.data);
      try {
        const r = await axios.get(`${API_BASE}/api/scenarios`);
        setStaticScenarios(r.data);
      } catch { setStaticScenarios(null); }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handlePredict = async (inputData) => {
    try {
      const response = await axios.post(`${API_BASE}/api/predict`, toApiPayload(inputData));
      setPrediction(response.data);
    } catch (err) {
      setError(err.message);
    }
  };

  const runLiveScenarios = async () => {
    setLiveLoading(true);
    setLiveError(null);
    try {
      const baseline = baselineForm;
      const baselineRes = await axios.post(`${API_BASE}/api/predict`, toApiPayload(baseline));
      const baselineDemand = baselineRes.data.prediction;

      const results = {};
      for (const sc of SCENARIOS) {
        const modified = sc.modify(baseline);
        const res = await axios.post(`${API_BASE}/api/predict`, toApiPayload(modified));
        const scenarioDemand = res.data.prediction;
        const change = scenarioDemand - baselineDemand;
        results[sc.key] = {
          baseline_demand: baselineDemand,
          scenario_demand: scenarioDemand,
          absolute_change: change,
          percentage_change: baselineDemand !== 0 ? (change / baselineDemand) * 100 : 0,
        };
      }
      setLiveResults(results);
    } catch (err) {
      setLiveError(err.message);
    } finally {
      setLiveLoading(false);
    }
  };

  if (loading) return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-600">Loading Electricity Demand Forecasting System...</p>
      </div>
    </div>
  );

  if (error && !modelInfo) return (
    <div className="min-h-screen bg-red-50 flex items-center justify-center">
      <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 rounded max-w-md">
        <p className="font-bold">Connection Error</p>
        <p>{error}</p>
        <p className="text-sm mt-2">Make sure the backend is running: <code>python -m uvicorn app:app --reload --port 8000</code></p>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Electricity Demand Forecasting System</h1>
              <p className="text-gray-600 mt-1">Advanced ML-Powered Energy Analytics Platform</p>
            </div>
            <div className="flex items-center space-x-4">
              <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-medium">System Online</span>
              <span className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-medium">
                {modelInfo?.model_type || 'RandomForest'}
              </span>
              {modelInfo?.total_predictions_made > 0 && (
                <span className="bg-purple-100 text-purple-800 px-3 py-1 rounded-full text-sm font-medium">
                  {modelInfo.total_predictions_made} Predictions
                </span>
              )}
              <button onClick={loadData}
                className="bg-gray-100 text-gray-800 px-3 py-1 rounded-full text-sm font-medium hover:bg-gray-200 transition-colors">
                Refresh
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-8">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            {['predict', 'scenarios', 'grid-lab', 'performance'].map((tab) => (
              <button key={tab} onClick={() => setActiveTab(tab)}
                className={`py-2 px-1 border-b-2 font-medium text-sm capitalize ${
                  activeTab === tab
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}>
                {tab === 'grid-lab' ? 'Grid Decision Lab' : tab}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

        {/* ── Predict Tab ── */}
        {activeTab === 'predict' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Demand Prediction</h3>
              <PredictionForm onPredict={handlePredict} />
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Prediction Result</h3>
              {prediction ? (
                <div className="text-center">
                  <div className="text-5xl font-bold text-blue-600 mb-2">
                    {prediction.prediction?.toFixed(2)} kW
                  </div>
                  <p className="text-gray-600 mb-1">Predicted Electricity Demand</p>
                  {prediction.prediction_number && (
                    <p className="text-sm text-gray-500">Session prediction #{prediction.prediction_number}</p>
                  )}
                  <div className="mt-4 text-left bg-gray-50 p-4 rounded">
                    <h4 className="font-medium mb-2">Input Summary (first 8 features):</h4>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      {Object.entries(prediction.input_features).slice(0, 8).map(([key, value]) => (
                        <div key={key} className="flex justify-between">
                          <span className="text-gray-600">{key}:</span>
                          <span className="font-medium">{value}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center text-gray-500 py-12">
                  <p className="text-lg">Fill in the form and click</p>
                  <p className="font-semibold">Make Prediction</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Scenarios Tab ── */}
        {activeTab === 'scenarios' && (
          <div className="space-y-6">

            {/* Baseline form */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-1">Live Scenario Analysis</h3>
              <p className="text-sm text-gray-500 mb-4">
                Set your baseline conditions below. Each scenario applies specific changes to this
                baseline and shows how demand shifts — recalculated live by the model.
              </p>
              <BaselineForm
                form={baselineForm}
                onChange={setBaselineForm}
                onRun={runLiveScenarios}
                loading={liveLoading}
              />
              {liveError && (
                <p className="text-red-600 text-sm mt-2">Error: {liveError}</p>
              )}
            </div>

            {/* Live results */}
            {liveResults && (
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">Live Results</h3>
                  <span className="bg-green-100 text-green-800 text-xs px-2 py-1 rounded-full font-medium">
                    Calculated by model
                  </span>
                </div>
                <ScenarioResultGrid results={liveResults} />
                <InsightPanel results={liveResults} />
              </div>
            )}

            {/* Pre-computed reference (shown only before first live run) */}
            {!liveResults && staticScenarios && (
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-lg font-semibold text-gray-900">Pre-computed Reference</h3>
                  <span className="bg-yellow-100 text-yellow-800 text-xs px-2 py-1 rounded-full font-medium">
                    Static — from notebook
                  </span>
                </div>
                <p className="text-sm text-gray-500 mb-4">
                  These are fixed results generated when Notebook 2 was run. Set your baseline above
                  and click <strong>Run Scenarios</strong> to get live results.
                </p>
                <ScenarioResultGrid results={staticScenarios.scenarios} />
                <InsightPanel results={staticScenarios.scenarios} />
              </div>
            )}

            {!liveResults && !staticScenarios && (
              <div className="bg-white rounded-lg shadow p-6 text-center text-gray-500 py-8">
                <p>No pre-computed data available. Click <strong>Run Scenarios</strong> above to generate live results.</p>
              </div>
            )}
          </div>
        )}

        {/* ── Grid Decision Lab Tab ── */}
        {activeTab === 'grid-lab' && <GridLab />}

        {/* ── Performance Tab ── */}
        {activeTab === 'performance' && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Model Performance</h3>
            <PerformancePanel />
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Baseline form for live scenario runner
// ---------------------------------------------------------------------------
const DAY_NAMES   = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
const MONTH_NAMES = ['January','February','March','April','May','June',
                     'July','August','September','October','November','December'];

function BaselineForm({ form, onChange, onRun, loading }) {
  const set = (field, value) => onChange((prev) => ({ ...prev, [field]: value }));
  const inputClass = "mt-1 block w-full rounded-md border border-gray-300 px-3 py-1.5 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-sm";
  const labelClass = "block text-sm font-medium text-gray-700";

  return (
    <div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <div>
          <label className={labelClass}>Temperature (°C)</label>
          <input type="number" step="0.1" value={form.Temperature}
            onChange={(e) => set('Temperature', parseFloat(e.target.value))} className={inputClass} />
        </div>
        <div>
          <label className={labelClass}>Humidity (%)</label>
          <input type="number" step="0.1" min="0" max="100" value={form.Humidity}
            onChange={(e) => set('Humidity', parseFloat(e.target.value))} className={inputClass} />
        </div>
        <div>
          <label className={labelClass}>Electricity Price (LKR/kWh)</label>
          <input type="number" step="0.1" min="0" value={form.ElectricityPrice}
            onChange={(e) => set('ElectricityPrice', parseFloat(e.target.value))} className={inputClass} />
        </div>
        <div>
          <label className={labelClass}>GDP (LKR)</label>
          <input type="number" step="10000" min="0" value={form.GDP}
            onChange={(e) => set('GDP', parseFloat(e.target.value))} className={inputClass} />
        </div>
        <div>
          <label className={labelClass}>Hour of Day (0–23)</label>
          <input type="number" min="0" max="23" value={form.HourOfDay}
            onChange={(e) => set('HourOfDay', parseInt(e.target.value))} className={inputClass} />
        </div>
        <div>
          <label className={labelClass}>Month</label>
          <select value={form.Month} onChange={(e) => set('Month', parseInt(e.target.value))} className={inputClass}>
            {MONTH_NAMES.map((name, i) => <option key={i+1} value={i+1}>{name}</option>)}
          </select>
        </div>
        <div>
          <label className={labelClass}>Day of Week</label>
          <select value={form.DayOfWeek} onChange={(e) => set('DayOfWeek', parseInt(e.target.value))} className={inputClass}>
            {DAY_NAMES.map((name, i) => <option key={i} value={i}>{name}</option>)}
          </select>
        </div>
        <div>
          <label className={labelClass}>Per Capita Energy Use (kWh)</label>
          <input type="number" step="1" min="0" value={form.PerCapitaEnergyUse}
            onChange={(e) => set('PerCapitaEnergyUse', parseFloat(e.target.value))} className={inputClass} />
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button
          onClick={onRun}
          disabled={loading}
          className="bg-indigo-600 text-white px-6 py-2 rounded hover:bg-indigo-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Running...' : 'Run Scenarios'}
        </button>
        <p className="text-xs text-gray-400">
          Runs 5 model predictions (1 baseline + 4 scenarios) and shows live demand changes.
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Scenario result grid (used for both live and static results)
// ---------------------------------------------------------------------------
function ScenarioResultGrid({ results }) {
  return (
    <div className="space-y-3">
      {SCENARIOS.map(({ key, label, description }) => {
        const data = results?.[key];
        if (!data) return null;
        const pct = roundClean(data.percentage_change, 1);
        const isUp = pct > 0;
        const absChange = roundClean(data.absolute_change, 0);
        return (
          <div key={key} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between">
              <div>
                <h4 className="font-semibold text-base">{label}</h4>
                <p className="text-sm text-gray-500">{description}</p>
              </div>
              <span className={`text-2xl font-bold ml-4 ${isUp ? 'text-red-600' : pct < 0 ? 'text-green-600' : 'text-gray-500'}`}>
                {isUp ? '+' : ''}{pct.toFixed(1)}%
              </span>
            </div>
            <div className="grid grid-cols-3 gap-3 mt-3">
              <div className="text-center p-2 bg-gray-50 rounded">
                <div className="text-lg font-bold text-gray-700">{data.baseline_demand?.toFixed(0)} kW</div>
                <div className="text-xs text-gray-500">Baseline</div>
              </div>
              <div className="text-center p-2 bg-gray-50 rounded">
                <div className="text-lg font-bold text-gray-700">{data.scenario_demand?.toFixed(0)} kW</div>
                <div className="text-xs text-gray-500">Scenario</div>
              </div>
              <div className={`text-center p-2 rounded ${isUp ? 'bg-red-50' : pct < 0 ? 'bg-green-50' : 'bg-gray-100'}`}>
                <div className={`text-lg font-bold ${isUp ? 'text-red-600' : pct < 0 ? 'text-green-600' : 'text-gray-500'}`}>
                  {isUp ? '+' : ''}{absChange} kW
                </div>
                <div className="text-xs text-gray-500">Change</div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Dynamic insight panel
// ---------------------------------------------------------------------------
function InsightPanel({ results }) {
  if (!results) return null;

  const insights = SCENARIOS.map(({ key, label }) => {
    const data = results[key];
    if (!data) return null;
    const pct = roundClean(data.percentage_change, 2);
    const abs = Math.abs(pct);
    let text = '';
    if (key === 'heat_wave')
      text = pct > 0
        ? `Higher cooling demand drives a ${pct.toFixed(1)}% surge`
        : `Cooling demand drops by ${abs.toFixed(1)}% — baseline already hot`;
    else if (key === 'cold_spell')
      text = pct < 0
        ? `Cold reduces cooling load; heating is more efficient (-${abs.toFixed(1)}%)`
        : `Heating dominates and raises demand by ${pct.toFixed(1)}%`;
    else if (key === 'price_shock')
      text = abs < 1
        ? `Price-inelastic: demand barely moves (${pct.toFixed(2)}%) despite doubled price`
        : `Price-sensitive: demand shifts ${pct.toFixed(1)}% with doubled price`;
    else if (key === 'economic_boom')
      text = abs < 1
        ? `GDP-inelastic: economic growth has minimal residential impact (${pct.toFixed(2)}%)`
        : `Economic growth shifts demand by ${pct.toFixed(1)}%`;
    return { label, text };
  }).filter(Boolean);

  return (
    <div className="mt-4 p-4 bg-yellow-50 border-l-4 border-yellow-400 rounded-r">
      <h5 className="font-semibold text-yellow-800 mb-2">Business Insights</h5>
      <ul className="text-sm text-yellow-700 space-y-1">
        {insights.map(({ label, text }) => (
          <li key={label}><strong>{label}:</strong> {text}</li>
        ))}
      </ul>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Prediction Form (single prediction tab)
// ---------------------------------------------------------------------------
function PredictionForm({ onPredict }) {
  const [formData, setFormData] = useState({
    Temperature: 28, Humidity: 80, WindSpeed: 2, Rainfall: 5,
    SolarIrradiance: 250, GDP: 1000, PerCapitaEnergyUse: 500,
    ElectricityPrice: 25, HourOfDay: 14, Month: 6, DayOfWeek: 2, PublicEvent: 0,
  });

  const set = (field, value) => setFormData((prev) => ({ ...prev, [field]: value }));

  const handleSubmit = (e) => {
    e.preventDefault();
    onPredict(formData);
  };

  const inputClass = "mt-1 block w-full rounded-md border border-gray-300 px-3 py-1.5 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-sm";
  const labelClass = "block text-sm font-medium text-gray-700";

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Weather</p>
        <div className="grid grid-cols-2 gap-4">
          <div><label className={labelClass}>Temperature (°C)</label>
            <input type="number" step="0.1" value={formData.Temperature}
              onChange={(e) => set('Temperature', parseFloat(e.target.value))} className={inputClass} /></div>
          <div><label className={labelClass}>Humidity (%)</label>
            <input type="number" step="0.1" min="0" max="100" value={formData.Humidity}
              onChange={(e) => set('Humidity', parseFloat(e.target.value))} className={inputClass} /></div>
          <div><label className={labelClass}>Wind Speed (m/s)</label>
            <input type="number" step="0.1" min="0" value={formData.WindSpeed}
              onChange={(e) => set('WindSpeed', parseFloat(e.target.value))} className={inputClass} /></div>
          <div><label className={labelClass}>Rainfall (mm)</label>
            <input type="number" step="0.1" min="0" value={formData.Rainfall}
              onChange={(e) => set('Rainfall', parseFloat(e.target.value))} className={inputClass} /></div>
          <div className="col-span-2"><label className={labelClass}>Solar Irradiance (W/m²)</label>
            <input type="number" step="1" min="0" value={formData.SolarIrradiance}
              onChange={(e) => set('SolarIrradiance', parseFloat(e.target.value))} className={inputClass} /></div>
        </div>
      </div>

      <div>
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Economic</p>
        <div className="grid grid-cols-2 gap-4">
          <div><label className={labelClass}>GDP (LKR)</label>
            <input type="number" step="1000" min="0" value={formData.GDP}
              onChange={(e) => set('GDP', parseFloat(e.target.value))} className={inputClass} /></div>
          <div><label className={labelClass}>Per Capita Energy Use (kWh)</label>
            <input type="number" step="0.1" min="0" value={formData.PerCapitaEnergyUse}
              onChange={(e) => set('PerCapitaEnergyUse', parseFloat(e.target.value))} className={inputClass} /></div>
          <div className="col-span-2"><label className={labelClass}>Electricity Price (LKR/kWh)</label>
            <input type="number" step="0.1" min="0" value={formData.ElectricityPrice}
              onChange={(e) => set('ElectricityPrice', parseFloat(e.target.value))} className={inputClass} /></div>
        </div>
      </div>

      <div>
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Time Context</p>
        <div className="grid grid-cols-2 gap-4">
          <div><label className={labelClass}>Hour of Day (0–23)</label>
            <input type="number" min="0" max="23" value={formData.HourOfDay}
              onChange={(e) => set('HourOfDay', parseInt(e.target.value))} className={inputClass} /></div>
          <div><label className={labelClass}>Month</label>
            <select value={formData.Month} onChange={(e) => set('Month', parseInt(e.target.value))} className={inputClass}>
              {MONTH_NAMES.map((name, i) => <option key={i+1} value={i+1}>{name}</option>)}
            </select></div>
          <div className="col-span-2"><label className={labelClass}>Day of Week</label>
            <select value={formData.DayOfWeek} onChange={(e) => set('DayOfWeek', parseInt(e.target.value))} className={inputClass}>
              {DAY_NAMES.map((name, i) => <option key={i} value={i}>{name}</option>)}
            </select></div>
        </div>
      </div>

      <div>
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Other</p>
        <div className="flex items-center space-x-3">
          <input id="publicEvent" type="checkbox" checked={formData.PublicEvent === 1}
            onChange={(e) => set('PublicEvent', e.target.checked ? 1 : 0)}
            className="h-4 w-4 text-blue-600 rounded border-gray-300" />
          <label htmlFor="publicEvent" className={labelClass}>Public Event / Holiday</label>
        </div>
      </div>

      <button type="submit"
        className="w-full bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors font-medium">
        Make Prediction
      </button>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Performance Display
// ---------------------------------------------------------------------------
function PerformanceDisplay({ stackingEnsemble, deploymentDecision }) {
  return (
    <div className="space-y-6">
      {stackingEnsemble && (
        <div>
          <h4 className="font-semibold mb-3">Stacking Ensemble (Research Extension)</h4>
          <div className="bg-gray-50 p-4 rounded space-y-3 text-sm">
            <InfoRow label="Base learners" value={friendlyModelList(stackingEnsemble.base_learners)} />
            <InfoRow label="Meta-learner selected" value={stackingEnsemble.meta_learner_selected} />
            <InfoRow label="Optuna trials" value={stackingEnsemble.meta_learner_search?.n_trials} />
            <div>
              <span className="text-gray-600">Meta-learner trust weights:</span>
              <div className="flex gap-4 mt-1">
                <span>rf: {((stackingEnsemble.meta_learner_trust_weights?.rf ?? 0) * 100).toFixed(2)}%</span>
                <span>gb: {((stackingEnsemble.meta_learner_trust_weights?.gb ?? 0) * 100).toFixed(2)}%</span>
                <span className="font-medium">lr: {((stackingEnsemble.meta_learner_trust_weights?.lr ?? 0) * 100).toFixed(2)}%</span>
              </div>
            </div>
            {deploymentDecision && (() => {
              // The automated rule (>0.0001 R2 gain AND <10% linear trust) is
              // re-derived here independently of deploy_stacking, so this
              // stays honest even when deployment overrides the rule, rather
              // than assuming deploy_stacking implies the rule passed.
              const meetsRule = deploymentDecision.test_r2_gain > deploymentDecision.epsilon
                && deploymentDecision.linear_base_learner_trust_share < 0.10;
              const wasOverridden = deploymentDecision.deploy_stacking && !meetsRule;
              return (
                <div className="pt-2 border-t border-gray-200">
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${
                        wasOverridden ? 'bg-amber-100 text-amber-700'
                          : deploymentDecision.deploy_stacking ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'
                      }`}
                    >
                      {deploymentDecision.deployed_model} deployed{wasOverridden && ' (overridden)'}
                    </span>
                    <span className="text-xs text-gray-500">
                      R² gain vs Random Forest: {deploymentDecision.test_r2_gain} · linear trust share: {(deploymentDecision.linear_base_learner_trust_share * 100).toFixed(1)}%
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    {wasOverridden
                      ? 'The automated rule recommended keeping Random Forest (no material accuracy gain, and the meta-learner leans heavily on the unbounded linear base learner). The stacking ensemble is deployed anyway by project decision, to showcase it as this component’s research contribution — be aware this carries real extrapolation risk in scenario testing (see Scenario Analysis section below).'
                      : deploymentDecision.deploy_stacking
                      ? 'The ensemble showed a real accuracy gain without leaning on the unbounded linear base learner, so it replaced Random Forest.'
                      : 'No material accuracy gain over Random Forest, and the meta-learner leans heavily on the linear base learner, so Random Forest stays deployed for scenario-analysis safety.'}
                  </p>
                </div>
              );
            })()}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------
function InfoRow({ label, value }) {
  return (
    <div className="flex justify-between">
      <span className="text-gray-600">{label}:</span>
      <span className="font-medium">{value ?? 'N/A'}</span>
    </div>
  );
}
