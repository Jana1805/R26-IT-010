import React, { useState } from 'react';
import ScenarioForm from './components/ScenarioForm';
import ResultCard from './components/ResultCard';
import RiskIndicator from './components/RiskIndicator';
import DemandChart from './components/DemandChart';
import './App.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

function App() {
  const [scenarioResult, setScenarioResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [compareMode, setCompareMode] = useState(false);
  const [baselineScenario, setBaselineScenario] = useState(null);

  const handleScenarioSubmit = async (scenarioData) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/scenarios/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(scenarioData),
      });
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      const result = await response.json();
      
      if (compareMode && baselineScenario) {
        // In compare mode, compare the new scenario with baseline
        handleCompare(baselineScenario, result);
      } else {
        setScenarioResult(result);
        setBaselineScenario(result); // Set as baseline for future comparisons
      }
    } catch (error) {
      console.error('Error running scenario:', error);
      setError(`Failed to analyze scenario: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleCompare = async (scenario1, scenario2) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/scenarios/compare`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          baseline_input: scenario1.scenario_input,
          modified_input: scenario2.scenario_input,
        }),
      });
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      const comparison = await response.json();
      setScenarioResult({
        ...scenario2,
        comparison: comparison.comparison,
      });
    } catch (error) {
      console.error('Error comparing scenarios:', error);
      setError(`Failed to compare scenarios: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleStartComparison = () => {
    setCompareMode(true);
    setBaselineScenario(scenarioResult);
  };

  const resetForm = () => {
    setScenarioResult(null);
    setCompareMode(false);
    setBaselineScenario(null);
    setError(null);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>🔌 AI-Based Electricity Demand Intelligence System</h1>
        <p>Advanced scenario analysis with AI-powered recommendations for energy planners</p>
        <p className="tagline">Predict demand, assess risks, and optimize grid operations</p>
      </header>

      {error && (
        <div className="error-banner">
          <strong>Error:</strong> {error}
          <button className="dismiss-btn" onClick={() => setError(null)}>×</button>
        </div>
      )}

      <main className="app-main">
        <div className="form-section">
          <ScenarioForm 
            onScenarioSubmit={handleScenarioSubmit} 
            loading={loading}
          />
        </div>

        {scenarioResult && (
          <div className="results-section">
            <div className="results-header">
              <h2>Analysis Results</h2>
              <div className="results-actions">
                {!compareMode && (
                  <button className="action-btn" onClick={handleStartComparison}>
                    Compare Scenarios
                  </button>
                )}
                <button className="action-btn secondary" onClick={resetForm}>
                  New Analysis
                </button>
              </div>
            </div>

            <div className="results-grid">
              <ResultCard 
                result={scenarioResult} 
                onCompare={() => handleStartComparison()}
              />
              
              <div className="charts-section">
                <RiskIndicator 
                  risk_score={scenarioResult.risk_assessment.risk_score}
                  risk_category={scenarioResult.risk_assessment.risk_category}
                />
                
                <DemandChart 
                  demand_curve={scenarioResult.prediction.demand_curve}
                  peak_demand={scenarioResult.prediction.peak_demand}
                />
              </div>
            </div>

            {scenarioResult.comparison && (
              <div className="comparison-section">
                <h3>Scenario Comparison</h3>
                <p>{scenarioResult.comparison.recommendation}</p>
              </div>
            )}
          </div>
        )}

        {!scenarioResult && (
          <div className="welcome-section">
            <div className="welcome-content">
              <h2>Welcome to the AI Electricity Advisor</h2>
              <p>Define a scenario using the form above to:</p>
              <ul>
                <li>🔮 Forecast electricity demand under different conditions</li>
                <li>⚠️ Assess grid risks and vulnerabilities</li>
                <li>💡 Receive AI-powered recommendations from Gemini</li>
                <li>📊 Compare multiple scenarios side-by-side</li>
                <li>📈 Optimize energy planning decisions</li>
              </ul>
              <div className="quick-start">
                <h3>Quick Start:</h3>
                <ol>
                  <li>Adjust temperature and industrial load sliders</li>
                  <li>Select weather and holiday conditions</li>
                  <li>Set renewable energy contribution</li>
                  <li>Click "Analyze Scenario" to see results</li>
                </ol>
              </div>
            </div>
          </div>
        )}
      </main>

      <footer className="app-footer">
        <p>AI Electricity Scenario Analysis System | IT4010 Research Project</p>
        <p>Backend: FastAPI + Python | Frontend: React + Vite | AI: Google Gemini API</p>
      </footer>
    </div>
  );
}

export default App;
