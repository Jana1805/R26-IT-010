# AI-Based Electricity Demand Intelligence System (Component 4 - AI Advisor)

## 📋 Project Overview

This is a production-grade **AI-powered Decision Support System** for electricity demand forecasting and scenario analysis. It uses advanced demand simulation, risk assessment, and Large Language Model (Gemini API) integration to provide intelligent recommendations to energy planners.

### Core Features

- **🔮 Scenario Builder**: Define electricity scenarios with temperature, industrial load, weather, and renewable energy parameters
- **📊 Demand Simulation**: Accurately forecast electricity demand based on scenario conditions
- **⚠️ Risk Intelligence Engine**: Compute risk scores and identify grid vulnerabilities
- **🤖 AI Advisor Module**: Use Gemini API for intelligent analysis and recommendations
- **📈 Scenario Comparison**: Compare multiple scenarios side-by-side with AI recommendations
- **🎨 Interactive Dashboard**: React + Vite frontend with real-time updates

### Technology Stack

- **Backend**: Python 3.14 + FastAPI
- **Frontend**: React 18 + Vite + Chart.js
- **Database**: MongoDB (optional, currently using in-memory storage)
- **AI/LLM**: Google Gemini API
- **Visualization**: ECharts / Chart.js
- **DevOps**: Docker (optional)

---

## 🚀 Installation & Setup

### Prerequisites

- Python 3.12+ (3.14 recommended)
- Node.js 18+
- Git

### Backend Setup

#### 1. Navigate to backend directory

```bash
cd backend
```

#### 2. Create Python virtual environment

```bash
# Using Python 3.14
py -m venv venv

# Or using Python 3.12 if 3.14 unavailable
py -3.12 -m venv venv

# Activate virtual environment
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1

# On Windows CMD:
.\venv\Scripts\activate

# On Linux/Mac:
source venv/bin/activate
```

#### 3. Install dependencies

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

#### 4. Configure environment variables

```bash
# Copy the example .env file
cp .env.example .env

# Edit .env and add your Gemini API key
# GEMINI_API_KEY=your_api_key_here
```

To get a Gemini API key:
1. Go to https://ai.google.dev/
2. Click "Get API Key"
3. Create a new project and generate API key
4. Copy the key to `.env` file

#### 5. Run the backend server

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at: **http://localhost:8000**

### Frontend Setup

#### 1. Navigate to frontend directory

```bash
cd frontend
```

#### 2. Install dependencies

```bash
npm install
```

#### 3. Configure API endpoint (if needed)

Edit `src/App.jsx` and update `API_BASE_URL` if backend is on a different host:

```javascript
const API_BASE_URL = 'http://localhost:8000/api';
```

#### 4. Run development server

```bash
npm run dev
```

The application will be available at: **http://localhost:5173**

---

## 🎯 Usage Guide

### Step 1: Define a Scenario

1. Open the application at http://localhost:5173
2. Use the form to set:
   - **Temperature Change** (-10 to +10°C)
   - **Industrial Load Change** (-50% to +100%)
   - **Day Type** (Normal, Weekend, Holiday)
   - **Weather Condition** (Sunny, Rainy, Extreme)
   - **Renewable Energy** (0-100%)

### Step 2: View Results

The system will display:
- **Demand Predictions**: Base, adjusted, and peak demand forecasts
- **Risk Assessment**: Risk score, category, and specific factors
- **AI Analysis**: Gemini-powered insights and recommendations
- **24-hour Demand Curve**: Visualization of hourly demand

### Step 3: Compare Scenarios

1. Save your first scenario
2. Click "Compare Scenarios"
3. Define a different scenario
4. View comparative analysis and recommendations

### Step 4: Export Results

- Export scenario reports as text files
- Share analysis results with stakeholders

---

## 🔌 API Endpoints

### Health Check

```http
GET /
GET /health
```

### Scenario Analysis

```http
POST /api/scenarios/analyze
Content-Type: application/json

{
  "temperature_change": 5,
  "industrial_load_change": 30,
  "holiday_type": "normal",
  "weather_condition": "sunny",
  "renewable_energy_contribution": 35,
  "scenario_name": "Summer Peak 2026"
}
```

**Response**: Complete scenario analysis with predictions, risk assessment, and AI insights

### Scenario Comparison

```http
POST /api/scenarios/compare
Content-Type: application/json

{
  "baseline_input": {...},
  "modified_input": {...}
}
```

### List Scenarios

```http
GET /api/scenarios?limit=10&offset=0
```

### Get Specific Scenario

```http
GET /api/scenarios/{scenario_id}
```

### Test Endpoint

```http
GET /api/test/scenario
```

Returns a pre-defined test scenario for development testing.

---

## 🧠 System Architecture

### Backend Components

#### 1. **Demand Simulation Engine** (`simulation_engine.py`)
- Calculates adjusted demand based on scenario parameters
- Applies weighted factors for temperature, industrial load, weather, etc.
- Generates 24-hour demand curve
- Formula: `adjusted_demand = base_demand * (temp_factor * industrial_factor * holiday_factor * weather_factor) - renewable_offset`

#### 2. **Risk Intelligence Engine** (`simulation_engine.py`)
- Computes risk score (0-100)
- Categorizes as Low, Medium, High, or Critical
- Identifies specific risk factors
- Calculates:
  - Demand spike probability
  - Peak threshold crossing risk
  - Regional load imbalance risk

#### 3. **AI Advisor Service** (`ai_advisor.py`)
- Integrates with Gemini API for intelligent analysis
- Provides context-aware recommendations
- Fallback rule-based advisor if API unavailable
- Features:
  - Detailed scenario analysis
  - Key insights extraction
  - Actionable recommendations
  - Risk mitigation strategies

#### 4. **FastAPI Routes** (`main.py`)
- RESTful API endpoints
- Request validation with Pydantic
- Error handling and CORS configuration
- In-memory scenario storage

### Frontend Components

#### 1. **ScenarioForm.jsx**
- Interactive form for scenario definition
- Real-time slider updates
- Input validation
- Responsive design

#### 2. **ResultCard.jsx**
- Displays complete scenario analysis
- Expandable sections for detailed information
- Export functionality
- AI insights presentation

#### 3. **RiskIndicator.jsx**
- Visual risk level display
- Color-coded severity indicators
- Risk factor breakdown

#### 4. **DemandChart.jsx**
- 24-hour demand curve visualization
- Peak demand indicators
- Interactive chart controls

### Data Models

```python
# Scenario Input
- temperature_change: float (-10 to +10)
- industrial_load_change: float (-50 to +100)
- holiday_type: str (holiday | weekend | normal)
- weather_condition: str (rainy | sunny | extreme)
- renewable_energy_contribution: float (0-100)

# Demand Prediction
- base_demand: MW
- adjusted_demand: MW
- peak_demand: MW
- demand_curve: [24-hour hourly values]
- load_distribution: {north, central, south}

# Risk Assessment
- risk_score: 0-100
- risk_category: Low | Medium | High | Critical
- risk_factors: [list of identified factors]
- recommendations: str
```

---

## 🔑 Key Algorithms

### Demand Calculation

1. **Temperature Factor**: +2.5% per °C (heating/cooling demand)
2. **Industrial Factor**: Linear multiplier (1.0 + industrial_change/100)
3. **Holiday Factor**: 0.85-1.00 (weekday consumption varies)
4. **Weather Factor**: 0.95-1.20 (extreme weather increases HVAC load)
5. **Renewable Offset**: Reduces grid demand by percentage

### Risk Scoring

```
Risk Score = (spike_prob × 30) + (threshold_prob × 40) + (imbalance_risk × 20) + penalties
```

- **Demand Spike**: High industrial/temperature changes
- **Threshold Crossing**: Predicted peak vs. historical max (11,900 MW)
- **Load Imbalance**: Regional variance analysis

### AI Analysis Prompts

The system sends structured context to Gemini including:
- Scenario parameters with human-readable descriptions
- Predicted demand curves
- Risk scores and factors
- Historical context

Gemini generates:
- Detailed technical analysis
- Key insights (4 items)
- Recommendations (3 items)
- Risk mitigation strategies
- Next steps for grid operators

---

## 🧪 Testing

### Test Backend API

```bash
# Using curl
curl -X GET http://localhost:8000/api/test/scenario

# Using Python requests
python -c "
import requests
response = requests.get('http://localhost:8000/api/test/scenario')
print(response.json())
"
```

### Test Frontend

```bash
# The frontend should connect automatically to the backend
# Check browser console (F12) for any errors
```

### Full End-to-End Test

1. Start backend: `uvicorn app.main:app --reload`
2. Start frontend: `npm run dev`
3. Define a test scenario
4. Verify results display correctly
5. Compare two scenarios
6. Export report

---

## 📊 Example Scenario

**"Summer Heatwave with Industrial Growth"**

- Temperature: +8°C
- Industrial Load: +45%
- Day Type: Normal weekday
- Weather: Extreme heat
- Renewable: 25%

**Expected Results:**
- Base Demand: 8,500 MW
- Adjusted Demand: ~10,800 MW (+27%)
- Peak Demand: ~15,100 MW
- Risk Category: HIGH to CRITICAL
- AI Recommendation: Activate demand response, increase reserve capacity

---

## 🛠️ Troubleshooting

### Backend Won't Start

**Error**: `ModuleNotFoundError: No module named 'fastapi'`

**Solution**:
```bash
# Make sure virtual environment is activated
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Frontend Can't Connect to Backend

**Error**: `CORS error` or `Failed to fetch`

**Solution**:
1. Check backend is running on port 8000
2. Update `API_BASE_URL` in `src/App.jsx`
3. Ensure CORS is enabled in `app/main.py`

### Gemini API Not Working

**Error**: `Failed to analyze scenario`

**Solution**:
1. Verify `GEMINI_API_KEY` is set in `.env`
2. Check API key is valid and has access
3. The system will use fallback rule-based advisor if API fails

### Python 3.14 Compatibility Issues

If packages won't install on Python 3.14:
- Use Python 3.12: `py -3.12 -m venv venv`
- Or install specific wheel versions without building from source

---

## 📚 Project Structure

```
R26-IT-010-main/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app & routes
│   │   ├── models/
│   │   │   └── scenario.py          # Pydantic models
│   │   ├── services/
│   │   │   ├── simulation_engine.py # Demand & risk engines
│   │   │   └── ai_advisor.py        # Gemini integration
│   │   ├── database/
│   │   │   └── connection.py        # MongoDB (future)
│   │   └── routes/
│   │       └── predict.py           # Prediction routes
│   ├── requirements.txt             # Python dependencies
│   ├── .env.example                 # Configuration template
│   └── venv/                        # Virtual environment
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ScenarioForm.jsx    # Input form
│   │   │   ├── ResultCard.jsx      # Results display
│   │   │   ├── RiskIndicator.jsx   # Risk visualization
│   │   │   └── DemandChart.jsx     # Demand graph
│   │   ├── App.jsx                 # Main component
│   │   ├── App.css                 # Styling
│   │   └── main.jsx                # Entry point
│   ├── package.json                # Node dependencies
│   ├── vite.config.js              # Vite configuration
│   └── index.html                  # HTML template
│
└── README.md                        # This file
```

---

## 🚀 Deployment

### Docker Deployment (Optional)

```bash
# Build Docker images
docker-compose build

# Start containers
docker-compose up
```

### Production Checklist

- [ ] Set `DEBUG=False` in `.env`
- [ ] Use strong `GEMINI_API_KEY`
- [ ] Configure MongoDB for persistence
- [ ] Set up HTTPS/SSL
- [ ] Configure production CORS origins
- [ ] Set `workers > 1` in uvicorn
- [ ] Enable logging and monitoring
- [ ] Test all API endpoints
- [ ] Load test the system

---

## 📝 License & Citation

This is part of the **IT4010 Research Project** for electricity demand forecasting and AI-powered grid operations.

---

## 🤝 Contributing

1. Create feature branch: `git checkout -b feature/new-feature`
2. Commit changes: `git commit -m "Add new feature"`
3. Push to branch: `git push origin feature/new-feature`
4. Create Pull Request

---

## 📞 Support

For issues or questions:
1. Check the Troubleshooting section
2. Review the API documentation
3. Check backend logs for error messages
4. Verify all dependencies are installed

---

**Happy Energy Planning! 🔌⚡**
