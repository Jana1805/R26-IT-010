from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.auth_routes import router as auth_router
from app.core import auth
from app.core.config import FRONTEND_URL

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
app.include_router(auth_router, prefix="/api")


@app.on_event("startup")
def init_auth_db():
    # Login must never stop the dashboard API from starting.
    try:
        auth.init_db()
    except Exception as e:  # pragma: no cover
        print(f"[auth] could not initialise users.db: {e}")


@app.get("/health")
def health():
    return {"status": "ok", "app": "Behaviour Intelligence API"}
