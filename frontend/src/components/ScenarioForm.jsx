import React, { useState } from 'react';
import '../styles/ScenarioForm.css';

const ScenarioForm = ({ onScenarioSubmit, loading = false }) => {
  const [formData, setFormData] = useState({
    temperature_change: 0,
    industrial_load_change: 0,
    holiday_type: 'normal',
    weather_condition: 'sunny',
    renewable_energy_contribution: 30,
    scenario_name: ''
  });

  const [errors, setErrors] = useState({});

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: ['temperature_change', 'industrial_load_change', 'renewable_energy_contribution'].includes(name)
        ? parseFloat(value)
        : value
    }));
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  const validateForm = () => {
    const newErrors = {};
    if (formData.temperature_change < -10 || formData.temperature_change > 10) {
      newErrors.temperature_change = 'Must be between -10 and +10°C';
    }
    if (formData.industrial_load_change < -50 || formData.industrial_load_change > 100) {
      newErrors.industrial_load_change = 'Must be between -50% and +100%';
    }
    if (formData.renewable_energy_contribution < 0 || formData.renewable_energy_contribution > 100) {
      newErrors.renewable_energy_contribution = 'Must be between 0% and 100%';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (validateForm()) {
      onScenarioSubmit(formData);
    }
  };

  return (
    <div className="scenario-form-container">
      <div className="form-header">
        <h2>Define Electricity Scenario</h2>
        <p>Set parameters to analyze demand forecast and risks</p>
      </div>

      <form onSubmit={handleSubmit} className="scenario-form">
        <div className="form-group">
          <label htmlFor="scenario_name">Scenario Name</label>
          <input
            type="text"
            id="scenario_name"
            name="scenario_name"
            value={formData.scenario_name}
            onChange={handleInputChange}
            placeholder="e.g., Summer Heatwave 2026"
            className="input-field"
          />
        </div>

        <div className="form-group">
          <label htmlFor="temperature_change">Temperature Change: <span className="value">{formData.temperature_change}°C</span></label>
          <div className="slider-container">
            <span className="slider-label">-10°C</span>
            <input
              type="range"
              id="temperature_change"
              name="temperature_change"
              min="-10"
              max="10"
              step="0.5"
              value={formData.temperature_change}
              onChange={handleInputChange}
              className="slider"
            />
            <span className="slider-label">+10°C</span>
          </div>
          {errors.temperature_change && <span className="error">{errors.temperature_change}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="industrial_load_change">Industrial Load Change: <span className="value">{formData.industrial_load_change}%</span></label>
          <div className="slider-container">
            <span className="slider-label">-50%</span>
            <input
              type="range"
              id="industrial_load_change"
              name="industrial_load_change"
              min="-50"
              max="100"
              step="5"
              value={formData.industrial_load_change}
              onChange={handleInputChange}
              className="slider"
            />
            <span className="slider-label">+100%</span>
          </div>
          {errors.industrial_load_change && <span className="error">{errors.industrial_load_change}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="holiday_type">Day Type</label>
          <select
            id="holiday_type"
            name="holiday_type"
            value={formData.holiday_type}
            onChange={handleInputChange}
            className="select-field"
          >
            <option value="normal">Normal Weekday</option>
            <option value="weekend">Weekend</option>
            <option value="holiday">Public Holiday</option>
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="weather_condition">Weather Condition</label>
          <select
            id="weather_condition"
            name="weather_condition"
            value={formData.weather_condition}
            onChange={handleInputChange}
            className="select-field"
          >
            <option value="sunny">Sunny</option>
            <option value="rainy">Rainy</option>
            <option value="extreme">Extreme</option>
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="renewable_energy_contribution">Renewable Energy: <span className="value">{formData.renewable_energy_contribution}%</span></label>
          <div className="slider-container">
            <span className="slider-label">0%</span>
            <input
              type="range"
              id="renewable_energy_contribution"
              name="renewable_energy_contribution"
              min="0"
              max="100"
              step="5"
              value={formData.renewable_energy_contribution}
              onChange={handleInputChange}
              className="slider"
            />
            <span className="slider-label">100%</span>
          </div>
          {errors.renewable_energy_contribution && <span className="error">{errors.renewable_energy_contribution}</span>}
        </div>

        <button type="submit" className="submit-btn" disabled={loading}>
          {loading ? 'Analyzing...' : 'Analyze Scenario'}
        </button>
      </form>
    </div>
  );
};

export default ScenarioForm;