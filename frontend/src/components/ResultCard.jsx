import React, { useState } from 'react';

const ResultCard = ({ result, onCompare }) => {
  const [expandedSection, setExpandedSection] = useState('prediction');

  if (!result) {
    return null;
  }

  const { scenario_input, prediction, risk_assessment, ai_advisor } = result;

  const getRiskColor = (category) => {
    switch (category) {
      case 'Critical': return '#ff4444';
      case 'High': return '#ffaa00';
      case 'Medium': return '#ffff00';
      case 'Low': return '#44ff44';
      default: return '#cccccc';
    }
  };

  return (
    <div className="result-card-container">
      <div className="result-header">
        <h2>Scenario Analysis Results</h2>
        {scenario_input.scenario_name && <p className="scenario-name">{scenario_input.scenario_name}</p>}
      </div>

      {/* Prediction Section */}
      <section className="result-section">
        <div className="section-header" onClick={() => setExpandedSection(expandedSection === 'prediction' ? '' : 'prediction')}>
          <h3>📊 Demand Prediction</h3>
          <span className="toggle-icon">{expandedSection === 'prediction' ? '▼' : '▶'}</span>
        </div>
        {expandedSection === 'prediction' && (
          <div className="section-content">
            <div className="metric-row">
              <span className="label">Base Demand:</span>
              <span className="value">{prediction.base_demand.toFixed(0)} MW</span>
            </div>
            <div className="metric-row">
              <span className="label">Adjusted Demand:</span>
              <span className="value highlight">{prediction.adjusted_demand.toFixed(0)} MW</span>
            </div>
            <div className="metric-row">
              <span className="label">Peak Demand:</span>
              <span className="value peak">{prediction.peak_demand.toFixed(0)} MW</span>
            </div>
            <div className="metric-row">
              <span className="label">Confidence:</span>
              <span className="value">{prediction.confidence_score}%</span>
            </div>
          </div>
        )}
      </section>

      {/* Risk Assessment Section */}
      <section className="result-section">
        <div className="section-header" onClick={() => setExpandedSection(expandedSection === 'risk' ? '' : 'risk')}>
          <h3>⚠️ Risk Assessment</h3>
          <div 
            className="risk-indicator" 
            style={{backgroundColor: getRiskColor(risk_assessment.risk_category)}}
          >
            {risk_assessment.risk_category}
          </div>
        </div>
        {expandedSection === 'risk' && (
          <div className="section-content">
            <div className="metric-row">
              <span className="label">Risk Score:</span>
              <span className="value">{risk_assessment.risk_score}/100</span>
            </div>
            <div className="metric-row">
              <span className="label">Risk Category:</span>
              <span className={`risk-badge risk-${risk_assessment.risk_category.toLowerCase()}`}>
                {risk_assessment.risk_category}
              </span>
            </div>
            <div className="metric-row">
              <span className="label">Demand Spike Risk:</span>
              <span className="value">{(risk_assessment.demand_spike_probability * 100).toFixed(1)}%</span>
            </div>
            <div className="metric-row">
              <span className="label">Peak Threshold Risk:</span>
              <span className="value">{(risk_assessment.peak_threshold_crossing * 100).toFixed(1)}%</span>
            </div>
            <div className="risk-factors">
              <h4>Risk Factors:</h4>
              <ul>
                {risk_assessment.risk_factors.map((factor, idx) => (
                  <li key={idx}>{factor}</li>
                ))}
              </ul>
            </div>
            <div className="recommendation-box">
              <strong>Recommendation:</strong> {risk_assessment.recommendation}
            </div>
          </div>
        )}
      </section>

      {/* AI Advisor Section */}
      <section className="result-section">
        <div className="section-header" onClick={() => setExpandedSection(expandedSection === 'ai' ? '' : 'ai')}>
          <h3>🤖 AI Advisor Analysis</h3>
          <span className="toggle-icon">{expandedSection === 'ai' ? '▼' : '▶'}</span>
        </div>
        {expandedSection === 'ai' && (
          <div className="section-content ai-section">
            <div className="analysis-text">
              <h4>Analysis:</h4>
              <p>{ai_advisor.analysis}</p>
            </div>

            <div className="insights-box">
              <h4>Key Insights:</h4>
              <ul className="insights-list">
                {ai_advisor.key_insights.map((insight, idx) => (
                  <li key={idx}>💡 {insight}</li>
                ))}
              </ul>
            </div>

            <div className="recommendations-box">
              <h4>Recommendations:</h4>
              <ul className="recommendations-list">
                {ai_advisor.recommendations.map((rec, idx) => (
                  <li key={idx}>✓ {rec}</li>
                ))}
              </ul>
            </div>

            <div className="mitigation-box">
              <h4>Risk Mitigation Strategies:</h4>
              <ul className="mitigation-list">
                {ai_advisor.risk_mitigation_strategies.map((strategy, idx) => (
                  <li key={idx}>⛔ {strategy}</li>
                ))}
              </ul>
            </div>

            <div className="next-steps-box">
              <h4>Next Steps:</h4>
              <p>{ai_advisor.next_steps}</p>
            </div>
          </div>
        )}
      </section>

      {/* Scenario Parameters */}
      <section className="result-section">
        <div className="section-header" onClick={() => setExpandedSection(expandedSection === 'params' ? '' : 'params')}>
          <h3>📋 Scenario Parameters</h3>
          <span className="toggle-icon">{expandedSection === 'params' ? '▼' : '▶'}</span>
        </div>
        {expandedSection === 'params' && (
          <div className="section-content params-section">
            <div className="param-item">
              <span>Temperature Change:</span> {scenario_input.temperature_change}°C
            </div>
            <div className="param-item">
              <span>Industrial Load:</span> {scenario_input.industrial_load_change}%
            </div>
            <div className="param-item">
              <span>Day Type:</span> {scenario_input.holiday_type}
            </div>
            <div className="param-item">
              <span>Weather:</span> {scenario_input.weather_condition}
            </div>
            <div className="param-item">
              <span>Renewable Energy:</span> {scenario_input.renewable_energy_contribution}%
            </div>
          </div>
        )}
      </section>

      {/* Actions */}
      <div className="result-actions">
        {onCompare && (
          <button className="action-btn compare-btn" onClick={() => onCompare(result)}>
            Compare with Another Scenario
          </button>
        )}
        <button className="action-btn export-btn" onClick={() => downloadResult(result)}>
          Export Report
        </button>
      </div>
    </div>
  );
};

const downloadResult = (result) => {
  const reportText = `ELECTRICITY DEMAND SCENARIO ANALYSIS REPORT
===============================================

Scenario: ${result.scenario_input.scenario_name || 'Unnamed'}

PARAMETERS:
- Temperature Change: ${result.scenario_input.temperature_change}°C
- Industrial Load Change: ${result.scenario_input.industrial_load_change}%
- Day Type: ${result.scenario_input.holiday_type}
- Weather: ${result.scenario_input.weather_condition}
- Renewable Energy: ${result.scenario_input.renewable_energy_contribution}%

PREDICTIONS:
- Base Demand: ${result.prediction.base_demand.toFixed(0)} MW
- Adjusted Demand: ${result.prediction.adjusted_demand.toFixed(0)} MW
- Peak Demand: ${result.prediction.peak_demand.toFixed(0)} MW
- Confidence: ${result.prediction.confidence_score}%

RISK ASSESSMENT:
- Risk Score: ${result.risk_assessment.risk_score}/100
- Risk Category: ${result.risk_assessment.risk_category}
- Recommendation: ${result.risk_assessment.recommendation}

AI ANALYSIS:
${result.ai_advisor.analysis}

KEY INSIGHTS:
${result.ai_advisor.key_insights.map(i => `- ${i}`).join('\n')}

RECOMMENDATIONS:
${result.ai_advisor.recommendations.map(r => `- ${r}`).join('\n')}
`;

  const element = document.createElement('a');
  element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(reportText));
  element.setAttribute('download', `scenario-report-${Date.now()}.txt`);
  element.style.display = 'none';
  document.body.appendChild(element);
  element.click();
  document.body.removeChild(element);
};

export default ResultCard;