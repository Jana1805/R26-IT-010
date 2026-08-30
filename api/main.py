"""FastAPI app bootstrap and router wiring."""

import warnings

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.core.config import (
    API_TITLE,
    API_DESCRIPTION,
    API_VERSION,
    ALLOWED_ORIGINS,
    Q_HAT,
    MC_SAMPLES_DEFAULT,
    LOOKBACK,
)
from api.core import state
from api.services.data_service import load_data
from api.routers.behaviour import router as behaviour_router
from api.routers.models import router as models_router

warnings.filterwarnings("ignore")

app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(models_router)
app.include_router(behaviour_router)


@app.on_event("startup")
async def startup():
    """Load the shared dataset; model packages remain lazy."""
    print("\n" + "=" * 70)
    print("EDIS Load Forecasting API - Startup")
    print("=" * 70 + "\n")

    try:
        raw_data = load_data()
        data_errors = {}
    except Exception:
        raw_data = None
        data_errors = {"data": ["Dataset could not be loaded"]}
    state.set_data(raw_data, data_errors)

    if state.RAW_DF is not None:
        print("\nDataset ready. Model packages will load lazily on first inference.")
    else:
        print("\nDataset unavailable. Data-backed endpoints will return 503.")

    if getattr(state, 'LOAD_ERRORS', None):
        print("\nStartup errors detected:")
        for k, errs in state.LOAD_ERRORS.items():
            print(f" - {k}:")
            for e in errs:
                print(f"    {e}")

    print(f"\n  Q_HAT = {Q_HAT} kW")
    print(f"  MC samples (default) = {MC_SAMPLES_DEFAULT}")
    print(f"  Lookback = {LOOKBACK}")
    print("  Ready.\n")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
