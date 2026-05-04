import React from 'react';

const RiskIndicator = ({ risk }) => {
  const getRiskColor = (risk) => {
    switch (risk.toLowerCase()) {
      case 'low':
        return '#4CAF50'; // Green
      case 'medium':
        return '#FF9800'; // Orange
      case 'high':
        return '#F44336'; // Red
      default:
        return '#9E9E9E'; // Grey
    }
  };

  const getRiskDescription = (risk) => {
    switch (risk.toLowerCase()) {
      case 'low':
        return 'Minimal impact on electricity demand';
      case 'medium':
        return 'Moderate changes expected';
      case 'high':
        return 'Significant demand fluctuations possible';
      default:
        return 'Risk assessment unavailable';
    }
  };

  return (
    <div className="risk-indicator">
      <h3>Risk Assessment</h3>
      <div
        className="risk-circle"
        style={{ backgroundColor: getRiskColor(risk) }}
      >
        <span className="risk-level">{risk}</span>
      </div>
      <p className="risk-description">{getRiskDescription(risk)}</p>
    </div>
  );
};

export default RiskIndicator;