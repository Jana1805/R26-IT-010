"""Integration smoke test + latency measurement for the Behaviour Intelligence API.

Not part of the component code base: written to gather thesis evidence. Uses
FastAPI's in-process TestClient and redirects every data/model directory to a
scratch workspace, so the POST pipeline endpoints can be exercised without
touching behaviour-intelligence/data or behaviour-intelligence/models.

Usage (interpreter needs fastapi, httpx, scikit-learn):
    python thesis_evidence\\scripts\\api_smoke_test.py <scratch_workspace_dir>
The workspace must contain data/raw/synthetic_realistic_load.csv (eval_all.py creates it).
"""
import json
import statistics
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
WS = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT / "behaviour-intelligence" / "backend"))

import fastapi
import sklearn
from fastapi.testclient import TestClient

from app.controllers import pipeline_controller as pc
from app.main import app
from app.services import analysis_service as svc

pc.DATA_RAW_DIR = WS / "data" / "raw"
pc.DATA_PROCESSED_DIR = svc.DATA_PROCESSED_DIR = WS / "data" / "processed"
pc.MODELS_DIR = WS / "models"
for f in ["model_comparison_cache.json", "anomaly_comparison_cache.json"]:
    (pc.MODELS_DIR / f).unlink(missing_ok=True)

client = TestClient(app)
results = []


def call(method, path, **kw):
    t = time.perf_counter()
    r = client.request(method, path, **kw)
    return r, (time.perf_counter() - t) * 1000


def check(name, method, path, expect, repeat=1, **kw):
    """expect(resp) -> (ok: bool, note: str)"""
    times, r = [], None
    for _ in range(repeat):
        r, ms = call(method, path, **kw)
        times.append(ms)
    try:
        ok, note = expect(r)
    except Exception as e:  # a failed expectation must not stop the run
        ok, note = False, f"{type(e).__name__}: {e}"
    results.append({"test": name, "method": method, "path": path, "http_status": r.status_code,
                    "passed": bool(ok), "calls": repeat, "median_ms": round(statistics.median(times), 1),
                    "min_ms": round(min(times), 1), "max_ms": round(max(times), 1),
                    "response_bytes": len(r.content), "note": note})
    print(("PASS" if ok else "FAIL"), name, f"{statistics.median(times):.1f} ms", note)
    return r


def ok_env(pred):
    return lambda r: (r.status_code == 200 and r.json()["success"] and pred(r.json()["data"]), r.json()["message"])


check("health", "GET", "/health", lambda r: (r.json() == {"status": "ok", "app": "Behaviour Intelligence API"}, ""), 20)
check("openapi schema served", "GET", "/openapi.json", lambda r: (len(r.json()["paths"]) == 12, f"{len(r.json()['paths'])} paths"))
# pipeline, in order
check("POST generate-daily-profiles", "POST", "/api/generate-daily-profiles",
      ok_env(lambda d: d == {"raw_rows": 189793, "cleaned_rows": 189793, "profile_days": 1977}))
check("POST run-clustering", "POST", "/api/run-clustering",
      ok_env(lambda d: d["best_k"] == 2 and d["silhouette_score"] == 0.4729 and d["dbscan_n_clusters"] == 1))
check("POST run-anomaly-detection", "POST", "/api/run-anomaly-detection",
      ok_env(lambda d: d["final_anomalies"] == 60 and d["zscore_anomalies"] == 0))
check("POST detect-peak-days", "POST", "/api/detect-peak-days", ok_env(lambda d: d["peak_days"] == 281))
check("POST generate-behavior-labels", "POST", "/api/generate-behavior-labels",
      ok_env(lambda d: d["label_counts"] == {"Normal Weekday Demand": 1279, "Holiday / Low Demand Day": 396,
                                             "Peak Demand Day": 281, "Abnormal Demand Day": 21}))
# read endpoints
r = check("GET dashboard-summary", "GET", "/api/dashboard-summary",
          ok_env(lambda d: d["total_days"] == 1977 and len(d["all_days"]) == 1977 and len(d["recent_abnormal_days"]) == 10
                 and d["normal_days"] + d["peak_days"] + d["abnormal_days"] + d["holiday_days"] == 1977), 20)
check("GET get-day-profile (valid date)", "GET", "/api/get-day-profile?date=2024-07-04",
      ok_env(lambda d: len(d["profile_points"]) == 96 and d["behavior_label"] == "Peak Demand Day"), 20)
check("GET get-day-profile (unknown date -> success=false)", "GET", "/api/get-day-profile?date=1999-01-01",
      lambda r: (r.status_code == 200 and r.json()["success"] is False and r.json()["data"] == {}, r.json()["message"]))
check("GET get-day-profile (missing param -> 422)", "GET", "/api/get-day-profile", lambda r: (r.status_code == 422, ""))
check("GET predict-future-behavior (future date)", "GET", "/api/predict-future-behavior?date=2026-10-12",
      ok_env(lambda d: d["match_strategy"] == "month + day-of-week" and abs(sum(d["probability_distribution"].values()) - 100) < 0.1), 20)
check("GET predict-future-behavior (invalid date -> success=false)", "GET", "/api/predict-future-behavior?date=not-a-date",
      lambda r: (r.status_code == 200 and r.json()["success"] is False, r.json()["message"][:80]))
check("GET model-comparison (cold, computes)", "GET", "/api/model-comparison",
      ok_env(lambda d: d["best_model"]["model_name"] == "K-Means" and d["cached"] is False))
check("GET model-comparison (cached)", "GET", "/api/model-comparison", ok_env(lambda d: d["cached"] is True), 20)
check("GET anomaly-comparison (cold, 20 bootstrap resamples)", "GET", "/api/anomaly-comparison",
      ok_env(lambda d: d["best_model"]["model_name"] == "Isolation Forest" and d["cached"] is False))
check("GET anomaly-comparison (cached)", "GET", "/api/anomaly-comparison", ok_env(lambda d: d["cached"] is True), 20)
check("GET download-report (all days)", "GET", "/api/download-report",
      lambda r: (r.headers["content-type"].startswith("text/csv") and "attachment" in r.headers["content-disposition"]
                 and len(r.text.strip().splitlines()) == 1978, f"{len(r.text.strip().splitlines()) - 1} data rows"), 5)
check("GET download-report (label filter)", "GET", "/api/download-report?label=Abnormal Demand Day",
      lambda r: (len(r.text.strip().splitlines()) == 22, f"{len(r.text.strip().splitlines()) - 1} data rows"), 5)
check("GET download-report (unknown label -> header only)", "GET", "/api/download-report?label=Nope",
      lambda r: (r.status_code == 200 and len(r.text.strip().splitlines()) == 1, "header row only"))
check("CORS allows http://localhost:3000", "GET", "/health",
      lambda r: (r.headers.get("access-control-allow-origin") == "http://localhost:3000", ""), headers={"Origin": "http://localhost:3000"})
check("CORS does not allow other origins", "GET", "/health",
      lambda r: ("access-control-allow-origin" not in r.headers, ""), headers={"Origin": "http://evil.example"})
# missing-artefact behaviour
(pc.DATA_PROCESSED_DIR / "behavior_labels.csv").rename(pc.DATA_PROCESSED_DIR / "behavior_labels.bak")
check("GET dashboard-summary before pipeline run -> success=false", "GET", "/api/dashboard-summary",
      lambda r: (r.json()["success"] is False and "Pipeline has not been run" in r.json()["message"], r.json()["message"]))
check("GET download-report before pipeline run -> 404", "GET", "/api/download-report", lambda r: (r.status_code == 404, r.json()["detail"]))
(pc.DATA_PROCESSED_DIR / "behavior_labels.bak").rename(pc.DATA_PROCESSED_DIR / "behavior_labels.csv")

import pandas as pd

out = ROOT / "thesis_evidence" / "tables"
pd.DataFrame(results).to_csv(out / "T23_api_smoke_test_and_latency.csv", index=False)
passed = sum(r["passed"] for r in results)
summary = {"python": sys.version.split()[0], "fastapi": fastapi.__version__, "sklearn": sklearn.__version__,
           "pandas": pd.__version__, "tests": len(results), "passed": passed, "failed": len(results) - passed}
json.dump(summary, open(out / "api_smoke_test_summary.json", "w"), indent=2)
print(json.dumps(summary))
