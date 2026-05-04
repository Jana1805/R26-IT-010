"""
Demand simulation engine - computes adjusted demand based on scenario parameters
"""
from typing import Dict, List, Tuple
import math


class DemandSimulationEngine:
    """Simulates electricity demand under various scenario conditions"""
    
    # Base demand for a typical day in MW (from historical data)
    BASE_DEMAND_MW = 8500
    
    # Peak demand multiplier (peak typically 1.4x average)
    PEAK_MULTIPLIER = 1.4
    
    # Hourly demand curve pattern (24-hour profile, normalized to 1.0)
    HOURLY_PATTERN = [
        0.65, 0.60, 0.55, 0.52, 0.50, 0.52, 0.60, 0.78,  # 0-7 (night to morning)
        0.92, 0.95, 0.98, 1.00, 0.98, 0.96, 0.95, 0.94,  # 8-15 (day peak)
        0.98, 1.00, 0.99, 0.96, 0.92, 0.88, 0.80, 0.72   # 16-23 (evening to night)
    ]
    
    def __init__(self):
        """Initialize simulation engine with base parameters"""
        self.base_demand = self.BASE_DEMAND_MW
        self.peak_multiplier = self.PEAK_MULTIPLIER
    
    def simulate_scenario(self, scenario: Dict) -> Dict:
        """
        Simulate demand under given scenario conditions
        
        Args:
            scenario: Dict with keys:
                - temperature_change: float (-10 to +10)
                - industrial_load_change: float (-50 to +100) in %
                - holiday_type: str (holiday, weekend, normal)
                - weather_condition: str (rainy, sunny, extreme)
                - renewable_energy_contribution: float (0-100) in %
        
        Returns:
            Dict with demand prediction results
        """
        # Calculate adjustment factors
        temp_factor = self._calculate_temperature_factor(scenario['temperature_change'])
        industrial_factor = self._calculate_industrial_factor(scenario['industrial_load_change'])
        holiday_factor = self._calculate_holiday_factor(scenario['holiday_type'])
        weather_factor = self._calculate_weather_factor(scenario['weather_condition'])
        
        # Apply renewable energy offset
        renewable_offset = self._calculate_renewable_offset(scenario['renewable_energy_contribution'])
        
        # Aggregate all factors
        total_multiplier = temp_factor * industrial_factor * holiday_factor * weather_factor
        
        # Calculate adjusted base demand
        adjusted_base = self.base_demand * total_multiplier
        
        # Apply renewable energy reduction
        adjusted_demand = adjusted_base - renewable_offset
        adjusted_demand = max(adjusted_demand, self.base_demand * 0.3)  # Floor at 30% of base
        
        # Generate 24-hour demand curve
        demand_curve = self._generate_demand_curve(adjusted_demand)
        
        # Calculate peak
        peak_demand = max(demand_curve)
        
        # Calculate load distribution across regions (simplified: 3 regions)
        load_distribution = self._calculate_regional_distribution(adjusted_demand)
        
        # Confidence based on scenario parameters
        confidence_score = self._calculate_confidence(scenario)
        
        return {
            'base_demand': self.base_demand,
            'adjusted_demand': round(adjusted_demand, 2),
            'peak_demand': round(peak_demand, 2),
            'demand_curve': [round(d, 2) for d in demand_curve],
            'load_distribution': load_distribution,
            'confidence_score': confidence_score,
            'factors_applied': {
                'temperature_factor': round(temp_factor, 3),
                'industrial_factor': round(industrial_factor, 3),
                'holiday_factor': round(holiday_factor, 3),
                'weather_factor': round(weather_factor, 3),
                'renewable_offset_mw': round(renewable_offset, 2)
            }
        }
    
    def _calculate_temperature_factor(self, temp_change: float) -> float:
        """
        Temperature impacts demand significantly
        +2.5% demand per 1°C increase (heating/cooling)
        Formula: 1.0 + (temp_change * 0.025)
        """
        factor = 1.0 + (temp_change * 0.025)
        # Clamp between 0.7 and 1.5 (70% to 150%)
        return max(0.7, min(1.5, factor))
    
    def _calculate_industrial_factor(self, industrial_change: float) -> float:
        """
        Industrial load change as percentage
        Linear relationship: 1.0 + (change / 100)
        """
        factor = 1.0 + (industrial_change / 100.0)
        # Clamp between 0.5 and 2.0
        return max(0.5, min(2.0, factor))
    
    def _calculate_holiday_factor(self, holiday_type: str) -> float:
        """
        Holiday/weekend reduces demand, normal increases
        """
        factors = {
            'holiday': 0.85,    # 15% reduction
            'weekend': 0.90,    # 10% reduction
            'normal': 1.00      # No change
        }
        return factors.get(holiday_type, 1.0)
    
    def _calculate_weather_factor(self, weather: str) -> float:
        """
        Weather impacts demand through temperature/humidity
        """
        factors = {
            'sunny': 1.08,      # Warmer, more AC use
            'rainy': 0.95,      # Cooler, less AC
            'extreme': 1.20     # Extreme weather = high HVAC load
        }
        return factors.get(weather, 1.0)
    
    def _calculate_renewable_offset(self, renewable_pct: float) -> float:
        """
        Renewable energy reduces required grid demand
        Assumes 1% renewable = 40 MW offset from grid
        """
        return (renewable_pct / 100.0) * 8500 * 0.05  # 5% of base per 100% renewable
    
    def _generate_demand_curve(self, adjusted_demand: float) -> List[float]:
        """
        Generate 24-hour demand profile based on adjusted demand
        """
        return [adjusted_demand * pattern for pattern in self.HOURLY_PATTERN]
    
    def _calculate_regional_distribution(self, total_demand: float) -> Dict[str, float]:
        """
        Distribute demand across regions
        Assuming: North 35%, Central 45%, South 20%
        """
        return {
            'north_region': round(total_demand * 0.35, 2),
            'central_region': round(total_demand * 0.45, 2),
            'south_region': round(total_demand * 0.20, 2),
            'total': round(total_demand, 2)
        }
    
    def _calculate_confidence(self, scenario: Dict) -> float:
        """
        Calculate confidence score based on scenario parameters
        Normal conditions = high confidence, extreme conditions = lower confidence
        """
        confidence = 85.0
        
        # Penalize for extreme parameters
        if abs(scenario['temperature_change']) > 8:
            confidence -= 10
        if abs(scenario['industrial_load_change']) > 50:
            confidence -= 10
        if scenario['weather_condition'] == 'extreme':
            confidence -= 5
        
        return max(60, min(95, confidence))


class RiskIntelligenceEngine:
    """Computes risk scores and factors for demand scenarios"""
    
    def __init__(self):
        """Initialize risk engine"""
        self.simulation_engine = DemandSimulationEngine()
    
    def assess_risk(self, scenario: Dict, prediction: Dict) -> Dict:
        """
        Assess risk level based on scenario and predictions
        
        Args:
            scenario: User scenario parameters
            prediction: Prediction results from simulation
        
        Returns:
            Dict with risk assessment
        """
        # Calculate individual risk factors
        spike_probability = self._calculate_spike_probability(scenario, prediction)
        threshold_probability = self._calculate_threshold_probability(prediction)
        imbalance_risk = self._calculate_imbalance_risk(prediction)
        
        # Calculate overall risk score (0-100)
        risk_score = self._calculate_risk_score(
            spike_probability,
            threshold_probability,
            imbalance_risk,
            scenario
        )
        
        # Determine risk category
        risk_category = self._categorize_risk(risk_score)
        
        # Identify risk factors
        risk_factors = self._identify_risk_factors(scenario, prediction, risk_score)
        
        # Generate recommendation
        recommendation = self._generate_recommendation(risk_category, risk_factors)
        
        return {
            'risk_score': round(risk_score, 1),
            'risk_category': risk_category,
            'risk_factors': risk_factors,
            'demand_spike_probability': round(spike_probability, 3),
            'peak_threshold_crossing': round(threshold_probability, 3),
            'load_imbalance_risk': round(imbalance_risk, 3),
            'recommendation': recommendation
        }
    
    def _calculate_spike_probability(self, scenario: Dict, prediction: Dict) -> float:
        """
        Probability that demand will spike significantly
        Based on industrial change, temperature, weather
        """
        probability = 0.2  # Base 20%
        
        if scenario['industrial_load_change'] > 30:
            probability += 0.2
        if scenario['temperature_change'] > 5:
            probability += 0.15
        if scenario['weather_condition'] == 'extreme':
            probability += 0.25
        
        return min(1.0, probability)
    
    def _calculate_threshold_probability(self, prediction: Dict) -> float:
        """
        Probability of exceeding historical peak demand (11,900 MW)
        """
        historical_peak = 11900
        predicted_peak = prediction['peak_demand']
        
        if predicted_peak >= historical_peak:
            return 0.9
        elif predicted_peak >= historical_peak * 0.95:
            return 0.6
        elif predicted_peak >= historical_peak * 0.90:
            return 0.3
        else:
            return 0.1
    
    def _calculate_imbalance_risk(self, prediction: Dict) -> float:
        """
        Risk of regional load imbalance
        Calculated from regional distribution variance
        """
        distribution = prediction['load_distribution']
        demands = [
            distribution['north_region'],
            distribution['central_region'],
            distribution['south_region']
        ]
        
        avg_demand = sum(demands) / len(demands)
        variance = sum([(d - avg_demand) ** 2 for d in demands]) / len(demands)
        std_dev = variance ** 0.5
        
        # Risk increases with variance
        risk = min(0.8, (std_dev / avg_demand) * 2)
        return risk
    
    def _calculate_risk_score(self, spike_prob: float, threshold_prob: float, 
                             imbalance_risk: float, scenario: Dict) -> float:
        """
        Aggregate individual risk factors into overall score
        """
        # Weighted combination
        score = (spike_prob * 30) + (threshold_prob * 40) + (imbalance_risk * 20)
        
        # Scenario parameter penalties
        if scenario['industrial_load_change'] > 50:
            score += 10
        if abs(scenario['temperature_change']) > 8:
            score += 10
        if scenario['weather_condition'] == 'extreme':
            score += 15
        
        return min(100, score)
    
    def _categorize_risk(self, risk_score: float) -> str:
        """Categorize risk level"""
        if risk_score < 25:
            return "Low"
        elif risk_score < 50:
            return "Medium"
        elif risk_score < 75:
            return "High"
        else:
            return "Critical"
    
    def _identify_risk_factors(self, scenario: Dict, prediction: Dict, risk_score: float) -> List[str]:
        """Identify and list specific risk factors"""
        factors = []
        
        if scenario['temperature_change'] > 5:
            factors.append(f"High temperature increase (+{scenario['temperature_change']}°C)")
        elif scenario['temperature_change'] < -5:
            factors.append(f"Significant temperature drop ({scenario['temperature_change']}°C)")
        
        if scenario['industrial_load_change'] > 30:
            factors.append(f"Heavy industrial load increase (+{scenario['industrial_load_change']}%)")
        
        if scenario['weather_condition'] == 'extreme':
            factors.append("Extreme weather condition expected")
        
        if prediction['peak_demand'] > 11500:
            factors.append(f"Peak demand very high ({prediction['peak_demand']} MW)")
        
        if scenario['renewable_energy_contribution'] < 10:
            factors.append("Low renewable energy contribution")
        
        if risk_score > 75:
            factors.append("Overall risk level is critical")
        
        return factors if factors else ["No major risk factors identified"]
    
    def _generate_recommendation(self, risk_category: str, risk_factors: List[str]) -> str:
        """Generate actionable recommendation based on risk"""
        if risk_category == "Critical":
            return "URGENT: Activate emergency protocols. Increase reserve capacity and prepare demand response programs."
        elif risk_category == "High":
            return "Alert grid operators. Monitor demand closely and prepare to engage demand response if needed."
        elif risk_category == "Medium":
            return "Monitor the situation. Standard operations should be sufficient but remain alert."
        else:
            return "Low risk scenario. Proceed with standard operations."
