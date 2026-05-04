# R26-IT-010
AI-Based Electricity Demand Intelligence System For Sri Lanka

A full-stack web application for simulating "what-if" scenarios in electricity demand forecasting using machine learning.

## Tech Stack

- **Backend**: Python FastAPI
- **Frontend**: React with Vite
- **Database**: MongoDB
- **ML Model**: XGBoost (pre-trained)

## Features

- **Demand Prediction**: Predict electricity demand based on weather and other features
- **Scenario Analysis**: Simulate changes in temperature, rainfall, and public events
- **Risk Assessment**: Automatic risk level calculation (Low, Medium, High)
- **Data Visualization**: Interactive charts showing baseline vs scenario comparisons
- **Data Persistence**: Store scenario results in MongoDB

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── routes/          # API endpoints
│   │   ├── services/        # Business logic
│   │   ├── models/          # Pydantic schemas
│   │   ├── database/        # MongoDB connection
│   │   ├── utils/           # Model loading utilities
│   │   └── main.py          # FastAPI app
│   ├── ml_model/            # Pre-trained XGBoost model
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml        # MongoDB setup
└── README.md
```

## Setup Instructions

### Prerequisites

- Python 3.8+
- Node.js 16+
- Docker and Docker Compose

### 1. Start MongoDB

```bash
docker-compose up -d
```

### 2. Backend Setup

```bash
cd backend
pip install -p requirements.txt
python -m app.main
```

The backend will run on http://localhost:8000

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will run on http://localhost:5173

## API Endpoints

### POST /api/predict
Predict electricity demand based on input features.

**Request Body:**
```json
{
  "temperature": 25.0,
  "rainfall": 50.0,
  "humidity": 60.0,
  "wind_speed": 5.0,
  "public_event": false
}
```

**Response:**
```json
{
  "predicted_demand": 150.5
}
```

### POST /api/scenario
Run scenario analysis with user-defined changes.

**Request Body:**
```json
{
  "baseline_temperature": 25.0,
  "baseline_rainfall": 50.0,
  "baseline_humidity": 60.0,
  "baseline_wind_speed": 5.0,
  "temperature_change": 5.0,
  "rainfall_change": -10.0,
  "public_event": true
}
```

**Response:**
```json
{
  "baseline": 150.5,
  "scenario": 165.2,
  "change_percent": 9.76,
  "risk": "Medium"
}
```

## Risk Assessment Logic

- **Low**: Change ≤ 5%
- **Medium**: 5% < Change ≤ 10%
- **High**: Change > 10%

## Usage

1. Set baseline weather conditions using the sliders
2. Adjust scenario parameters (temperature change, rainfall change, public event)
3. Click "Run Scenario Analysis"
4. View the results including demand predictions, percentage change, and risk level
5. Analyze the chart comparing baseline vs scenario demand

## Development

- Backend uses modular structure with separate folders for routes, services, models, etc.
- Frontend uses React functional components with hooks
- Data visualization powered by Recharts
- CORS enabled for frontend-backend communication

## License

This project is for educational purposes.
