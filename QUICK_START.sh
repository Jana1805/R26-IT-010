#!/usr/bin/env bash
# Quick Start Commands for AI Electricity Scenario Analysis System

# ========================================
# BACKEND SETUP & LAUNCH
# ========================================

# Navigate to backend
cd backend

# Activate virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate virtual environment (Linux/Mac)
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file from example
copy .env.example .env
# Edit .env and add your GEMINI_API_KEY

# Run backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Test backend is running
curl http://localhost:8000/
# or open in browser: http://localhost:8000/docs (Swagger UI)


# ========================================
# FRONTEND SETUP & LAUNCH
# ========================================

# In a new terminal, navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview


# ========================================
# API TESTING (use curl or Postman)
# ========================================

# Test basic scenario
curl -X GET http://localhost:8000/api/test/scenario

# Analyze a custom scenario
curl -X POST http://localhost:8000/api/scenarios/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "temperature_change": 5,
    "industrial_load_change": 30,
    "holiday_type": "normal",
    "weather_condition": "sunny",
    "renewable_energy_contribution": 35,
    "scenario_name": "Summer Peak Scenario"
  }'

# Compare two scenarios
curl -X POST http://localhost:8000/api/scenarios/compare \
  -H "Content-Type: application/json" \
  -d '{
    "baseline_input": {...},
    "modified_input": {...}
  }'

# List all scenarios
curl http://localhost:8000/api/scenarios

# Get specific scenario
curl http://localhost:8000/api/scenarios/{scenario_id}


# ========================================
# DOCKER DEPLOYMENT (Optional)
# ========================================

# Build and run with Docker Compose
docker-compose build
docker-compose up

# Check logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop services
docker-compose down


# ========================================
# TROUBLESHOOTING COMMANDS
# ========================================

# Check Python version
python --version

# Check pip packages
pip list | grep -E "fastapi|uvicorn|pydantic"

# Check if port 8000 is in use
netstat -ano | findstr :8000

# Kill process on port 8000 (Windows)
taskkill /PID {PID} /F

# Check npm packages
npm list --depth=0

# Clear npm cache
npm cache clean --force

# Reinstall node_modules
rm -rf node_modules
npm install


# ========================================
# DEVELOPMENT WORKFLOW
# ========================================

# 1. Terminal 1: Backend development
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload

# 2. Terminal 2: Frontend development
cd frontend
npm run dev

# 3. Terminal 3: Testing/Debugging
# Run API tests and check console output

# 4. Editor: Edit code in src/ directory
# Backend: app/main.py, app/services/*, app/models/*
# Frontend: src/components/*, src/App.jsx


# ========================================
# KEY ENDPOINTS REFERENCE
# ========================================

# Health Check
GET http://localhost:8000/
GET http://localhost:8000/health

# Analyze Scenario
POST http://localhost:8000/api/scenarios/analyze

# Compare Scenarios
POST http://localhost:8000/api/scenarios/compare

# List Scenarios
GET http://localhost:8000/api/scenarios

# Get Scenario Details
GET http://localhost:8000/api/scenarios/{scenario_id}

# Swagger API Documentation
GET http://localhost:8000/docs

# ReDoc API Documentation
GET http://localhost:8000/redoc


# ========================================
# GEMINI API SETUP
# ========================================

# 1. Go to https://ai.google.dev/
# 2. Click "Get API Key"
# 3. Create new project
# 4. Generate API key
# 5. Copy key to .env:
#    GEMINI_API_KEY=your_key_here
# 6. Restart backend server


# ========================================
# PRODUCTION DEPLOYMENT
# ========================================

# Backend: Multi-worker production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Frontend: Build for production
npm run build
# Output: dist/ directory

# Serve frontend (using simple HTTP server)
python -m http.server 3000 --directory dist

# Or using Node server
npx serve dist


# ========================================
# USEFUL VARIABLES
# ========================================

# Temperature range: -10°C to +10°C
# Industrial load: -50% to +100%
# Renewable energy: 0% to 100%
# Day types: normal, weekend, holiday
# Weather: sunny, rainy, extreme
# Risk categories: Low, Medium, High, Critical
# Risk scores: 0-25 (Low), 25-50 (Medium), 50-75 (High), 75-100 (Critical)

