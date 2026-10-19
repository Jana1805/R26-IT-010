# Electricity Demand Forecasting - Scenario Analysis Backend

A production-ready FastAPI backend for scenario analysis and decision support in electricity demand forecasting.

## Overview

This backend system enables users to:
- Run "what-if" scenario analyses on electricity demand predictions
- Modify input parameters (temperature, rainfall, events)
- Compare baseline vs. scenario predictions
- Assess risk levels
- Receive actionable recommendations
- Store results in MongoDB

## Tech Stack

- **Python 3.9+**
- **FastAPI** - Modern async web framework
- **MongoDB** - Document database for result storage
- **Scikit-learn** - Machine learning model compatibility
- **Joblib** - Model serialization
- **Uvicorn** - ASGI server

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py         # Configuration and environment variables
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   └── mongodb.py          # MongoDB connection and operations
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── scenario.py         # Scenario analysis endpoints
│   │   └── health.py           # Health check endpoints
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── model_service.py    # Model loading and prediction
│   │   ├── risk_service.py     # Risk classification
│   │   ├── recommendation_service.py  # Recommendation generation
│   │   └── scenario_service.py # Scenario orchestration
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── scenario_schema.py  # Pydantic request/response schemas
│   │
│   └── utils/
│       ├── __init__.py
│       ├── data_modifier.py    # Data modification logic
│       └── validators.py       # Input validation
│
├── saved_models/
│   ├── forecast_model.pkl      # Trained demand forecasting model
│   ├── feat_scaler.pkl         # Feature scaler (StandardScaler)
│   └── target_scaler.pkl       # Target scaler (StandardScaler)
│
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables
├── setup_models.py            # Setup script for mock models
├── README.md                  # This file
└── run.sh                     # Run script (optional)
```

## Installation

### Prerequisites

- Python 3.9 or higher
- MongoDB 4.0 or higher (for production; optional for testing)
- pip or conda

### Setup

1. **Clone or download the project:**
   ```bash
   cd backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment:**
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Setup mock models (for testing):**
   ```bash
   python setup_models.py
   ```
   
   This creates dummy trained models. For production, replace with actual trained models.

6. **Configure environment:**
   
   Edit `.env` file with your settings:
   ```env
   MONGODB_URI=mongodb://localhost:27017
   MONGODB_DB=demand_forecasting
   LOG_LEVEL=INFO
   ```

## How to Run This Backend

Use the project virtual environment so the correct Python version and packages are used.

### Windows

```bat
cd C:\final_research\backend
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe setup_models.py
venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001 --app-dir C:\final_research\backend
```

The backend will run at:

```text
http://127.0.0.1:8001
```

Open the API docs:

```text
http://127.0.0.1:8001/docs
```

Health check:

```text
http://127.0.0.1:8001/api/health
```

### macOS/Linux

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python setup_models.py
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

### Important Notes

- The correct FastAPI app path is `app.main:app`.
- Do not run `python main.py`; there is no `main.py` in the backend root.
- If `forecast_model.pkl` is missing, the backend can auto-generate a fallback model.
- MongoDB is optional for demo mode. If MongoDB is offline, predictions still work, but scenario history may be empty.
- This project currently uses port `8001` because another older API may already be using port `8000`.

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 4
```

## API Endpoints

### Health Checks

#### GET `/api/health`
Basic health check
```bash
curl http://localhost:8000/api/health
```

Response:
```json
{
  "status": "ok",
  "message": "Application is running",
  "app": "Electricity Demand Forecasting - Scenario Analysis",
  "version": "1.0.0"
}
```

#### GET `/api/health/detailed`
Detailed health check with all components

#### GET `/api/health/ready`
Kubernetes-style readiness probe

### Scenario Analysis

#### POST `/api/run-scenario`
Run a scenario analysis

Request body:
```json
{
  "input": {
    "temperature": 25.5,
    "rainfall": 50.0,
    "humidity": 65.0,
    "wind_speed": 10.5,
    "dayofweek": 3,
    "month": 6,
    "hour": 14
  },
  "scenario": {
    "temperature": 2.0,
    "rainfall": 10.0,
    "event": 0
  }
}
```

Response:
```json
{
  "baseline": 125.5,
  "scenario": 134.2,
  "change_percent": 6.95,
  "risk": "MEDIUM",
  "recommendation": "Monitor demand closely",
  "detailed_recommendation": {
    "recommendation": "Monitor demand closely",
    "priority": "medium",
    "details": "Moderate demand change detected...",
    "actions": [...],
    "context": {...}
  },
  "timestamp": "2024-01-15T10:30:45.123456",
  "scenario_id": "507f1f77bcf86cd799439011"
}
```

#### GET `/api/scenario-history?limit=100`
Get history of scenario analyses

#### GET `/api/scenario/{result_id}`
Get a specific scenario result

## Input Validation

### Baseline Input

- **temperature**: float (°C)
- **rainfall**: float (mm)
- **humidity**: float (0-100 %)
- **wind_speed**: float (≥ 0)
- **dayofweek**: int (0-6, Monday=0)
- **month**: int (1-12)
- **hour**: int (0-23)

### Scenario Parameters

- **temperature**: float (-20 to 20 °C change)
- **rainfall**: float (-100 to 100 mm change)
- **event**: int (0 or 1)

## Risk Classification

| Risk Level | Change Range | Action |
|-----------|-------------|--------|
| **LOW** | < 5% | No action needed |
| **MEDIUM** | 5% - 10% | Monitor demand closely |
| **HIGH** | > 10% | Increase generation capacity |

## Configuration

### Environment Variables (.env)

```env
# Application
APP_NAME=Electricity Demand Forecasting - Scenario Analysis
APP_VERSION=1.0.0
DEBUG=False

# MongoDB
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=demand_forecasting

# Models
MODEL_PATH=saved_models/forecast_model.pkl
SCALER_FEAT_PATH=saved_models/feat_scaler.pkl
SCALER_TARGET_PATH=saved_models/target_scaler.pkl

# Logging
LOG_LEVEL=INFO
```

## Database

### MongoDB Collections

#### scenario_results
Stores scenario analysis results:
```json
{
  "_id": ObjectId("..."),
  "baseline_input": {...},
  "scenario_params": {...},
  "baseline_prediction": 125.5,
  "scenario_prediction": 134.2,
  "change_percent": 6.95,
  "risk_level": "MEDIUM",
  "recommendation": "Monitor demand closely",
  "timestamp": ISODate("2024-01-15T10:30:45.123Z")
}
```

## Error Handling

The API returns appropriate HTTP status codes:

| Status | Meaning |
|--------|---------|
| 200 | Success |
| 400 | Bad request (analysis error) |
| 404 | Not found |
| 422 | Validation error |
| 500 | Server error |
| 503 | Service unavailable |

Error response format:
```json
{
  "detail": "Error message describing what went wrong"
}
```

## Logging

Logs are written to stdout with the following format:
```
YYYY-MM-DD HH:MM:SS - logger_name - LEVEL - message
```

Control log level with `LOG_LEVEL` environment variable:
- DEBUG: Detailed debugging information
- INFO: General informational messages
- WARNING: Warning messages
- ERROR: Error messages
- CRITICAL: Critical system failures

## Testing

### Quick Test Script

Create `test_api.py`:
```python
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    response = requests.get(f"{BASE_URL}/api/health")
    print("Health Check:", response.json())

def test_scenario():
    payload = {
        "input": {
            "temperature": 25.5,
            "rainfall": 50.0,
            "humidity": 65.0,
            "wind_speed": 10.5,
            "dayofweek": 3,
            "month": 6,
            "hour": 14
        },
        "scenario": {
            "temperature": 2.0,
            "rainfall": 10.0,
            "event": 0
        }
    }
    response = requests.post(f"{BASE_URL}/api/run-scenario", json=payload)
    print("Scenario Result:", json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    test_health()
    test_scenario()
```

Run with:
```bash
python test_api.py
```

## Deployment

### Docker

Create `Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t demand-forecasting-backend .
docker run -p 8000:8000 \
  -e MONGODB_URI=mongodb://mongo:27017 \
  -e MONGODB_DB=demand_forecasting \
  demand-forecasting-backend
```

### Kubernetes

Example deployment manifest:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demand-forecasting-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: demand-forecasting
  template:
    metadata:
      labels:
        app: demand-forecasting
    spec:
      containers:
      - name: api
        image: demand-forecasting-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: MONGODB_URI
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: mongodb_uri
        livenessProbe:
          httpGet:
            path: /api/health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

## API Documentation

Interactive API documentation available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Performance Considerations

- Model predictions are cached in memory
- Database connection is reused via singleton pattern
- Requests are handled asynchronously
- Consider using connection pooling for MongoDB in production
- Monitor memory usage with large batch predictions

## Security

For production deployment:

1. Set `DEBUG=False` in `.env`
2. Configure CORS properly (restrict origins)
3. Use HTTPS
4. Implement authentication (JWT, API keys)
5. Add rate limiting
6. Use environment variables for sensitive data
7. Enable MongoDB authentication
8. Use private networks for database connections

Example CORS configuration:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)
```

## Contributing

When modifying the codebase:

1. Follow PEP 8 style guide
2. Add docstrings to all functions and classes
3. Include type hints
4. Write unit tests for new features
5. Update documentation

## Troubleshooting

### MongoDB Connection Error
```
Failed to connect to MongoDB: ...
```
Solution: Ensure MongoDB is running:
```bash
# macOS with Homebrew
brew services start mongodb-community

# Linux
sudo systemctl start mongod

# Windows
net start MongoDB
```

### Model Files Not Found
```
Model file not found: saved_models/forecast_model.pkl
```
Solution: Run setup script:
```bash
python setup_models.py
```

### Port Already in Use
```
Address already in use
```
Solution: Use different port:
```bash
uvicorn app.main:app --port 8001
```

### ImportError
Ensure virtual environment is activated and packages installed:
```bash
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## License

Proprietary - Electricity Demand Forecasting Project

## Support

For issues or questions, contact the development team.
