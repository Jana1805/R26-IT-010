import sys
from pathlib import Path

# Add project root to Python path for absolute imports
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import router
from backend.app.core.config import BACKEND_PORT, FRONTEND_URL

app = FastAPI(
    title="Behaviour Intelligence API",
    version="1.0.0",
    description="AI-Based Electricity Demand Behaviour Intelligence System",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok", "app": "Behaviour Intelligence API"}
