"""Grid Decision Lab endpoints: regional demand, calibrated overload risk, levers, auto-recommend, live weather.

IMPORTANT data note: the training data has no geography. Regional shares, headroom factors and
temperature offsets below are ILLUSTRATIVE ASSUMPTIONS (documented in the UI). Province boundaries
(geoBoundaries) and live temperature/humidity (Open-Meteo) are real; regional demand is model-simulated.
"""
import json
import os
import time
import urllib.request
from typing import Any, Dict

import numpy as np
import pandas as pd
from fastapi import HTTPException

# share = assumed share of national demand; headroom = assumed relative spare capacity; offset = fallback temp offset (C)
REGIONS = [
    dict(key="Western", city="Colombo", lat=6.93, lon=79.86, share=0.43, headroom=0.96, offset=0.0),
    dict(key="Central", city="Kandy", lat=7.29, lon=80.63, share=0.10, headroom=1.02, offset=-4.0),
    dict(key="Southern", city="Galle", lat=6.03, lon=80.22, share=0.09, headroom=1.04, offset=0.0),
    dict(key="North Western", city="Kurunegala", lat=7.49, lon=80.36, share=0.10, headroom=1.00, offset=1.0),
    dict(key="Sabaragamuwa", city="Ratnapura", lat=6.68, lon=80.40, share=0.07, headroom=1.05, offset=-1.0),
    dict(key="Eastern", city="Trincomalee", lat=8.57, lon=81.23, share=0.06, headroom=0.98, offset=2.0),
    dict(key="North Central", city="Anuradhapura", lat=8.31, lon=80.40, share=0.05, headroom=1.00, offset=2.0),
    dict(key="Uva", city="Badulla", lat=6.99, lon=81.06, share=0.05, headroom=1.08, offset=-3.0),
    dict(key="Northern", city="Jaffna", lat=9.67, lon=80.01, share=0.05, headroom=1.06, offset=2.0),
]
_norm = sum(r["share"] * r["headroom"] for r in REGIONS)
for r in REGIONS:
    r["headroom"] = r["headroom"] / _norm  # so regional capacities add up to the national capacity
PEAK = list(range(17, 22))                 # 5 PM - 9 PM evening peak window
OFFPEAK = [22, 23, 0, 1, 2, 3, 4, 5]       # where shifted load lands (assumption: flexible night-time loads)
_weather_cache: Dict[str, Any] = {"t": 0, "data": None}


def register(app, model, features, reference, saved_dir):
    conf = json.load(open(os.path.join(saved_dir, "conformal.json")))
    resid = np.array(conf["residual_quantiles"])

    def p_over(headroom_kw):
        """P(model error > headroom) from the empirical (calibration) residual distribution."""
        idx = np.searchsorted(resid, headroom_kw, side="right")
        return 1.0 - np.clip(idx / len(resid), 0.0, 1.0)

    def fetch_weather():
        if time.time() - _weather_cache["t"] < 900 and _weather_cache["data"]:
            return _weather_cache["data"]
        lat = ",".join(str(r["lat"]) for r in REGIONS); lon = ",".join(str(r["lon"]) for r in REGIONS)
        url = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s&current=temperature_2m,relative_humidity_2m"
               "&hourly=temperature_2m,relative_humidity_2m&forecast_days=1&timezone=Asia%%2FColombo" % (lat, lon))
        with urllib.request.urlopen(url, timeout=8) as resp:
            raw = json.loads(resp.read())
        raw = raw if isinstance(raw, list) else [raw]
        data = {
            "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "time": raw[0]["current"]["time"],
            "regions": {r["key"]: dict(now_temp=raw[i]["current"]["temperature_2m"], now_humidity=raw[i]["current"]["relative_humidity_2m"],
                                       temp=raw[i]["hourly"]["temperature_2m"][:24], humidity=raw[i]["hourly"]["relative_humidity_2m"][:24])
                        for i, r in enumerate(REGIONS)},
        }
        _weather_cache.update(t=time.time(), data=data)
        return data

    @app.get("/api/live-weather")
    def live_weather():
        try:
            return fetch_weather()
        except Exception as e:  # network / API problems must not break the lab
            raise HTTPException(status_code=502, detail=f"Live weather unavailable: {e}")

    @app.get("/api/regions")
    def regions():
        return {"regions": [{k: r[k] for k in ("key", "city", "lat", "lon", "share", "headroom", "offset")} for r in REGIONS],
                "peak_hours": PEAK, "offpeak_hours": OFFPEAK}

    def _context(body):
        """Resolve weather per region/hour plus calendar fields."""
        source = body.get("source", "scenario"); live = None; month, dow = body.get("month", 6), body.get("dow", 2)
        delta = float(body.get("temp_delta", 0))
        if source == "live":
            live = fetch_weather()
            t = pd.Timestamp(live["time"]); month, dow = int(t.month), int(t.dayofweek)
            if body.get("dow_override") is not None:  # UI day-type filter (weekday / weekend / holiday)
                dow = int(body["dow_override"])
        T = np.zeros((len(REGIONS), 24)); H = np.zeros((len(REGIONS), 24))
        for i, r in enumerate(REGIONS):
            if live:
                T[i] = np.array(live["regions"][r["key"]]["temp"]) + delta
                H[i] = np.array(live["regions"][r["key"]]["humidity"])
            else:
                T[i] = float(body.get("temp", 28)) + r["offset"]; H[i] = float(body.get("humidity", 80))
        return T, H, month, dow, live

    def _regional_demand(body, T, H, month, dow, tariff):
        """[regions x 24] demand in kW from the model; tariff applies only in the evening peak window."""
        rows = []
        base = dict(reference["typical"])
        base.update({"Month": month, "Day of Week": dow, "Poya Day": int(body.get("poya", 0)), "Public Event": int(body.get("event", 0)),
                     "Electricity Price (LKR/kWh)": float(body.get("price", base["Electricity Price (LKR/kWh)"])),
                     "GDP (LKR)": float(body.get("gdp", base["GDP (LKR)"]))})
        for i in range(len(REGIONS)):
            for h in range(24):
                row = dict(base); row["Hour of Day"] = h; row["Temperature (°C)"] = float(T[i, h]); row["Humidity (%)"] = float(H[i, h])
                if h in PEAK: row["Electricity Price (LKR/kWh)"] *= 1 + tariff
                rows.append(row)
        pred = np.clip(model.predict(pd.DataFrame(rows)[features]), 0, None).reshape(len(REGIONS), 24)
        return pred * np.array([r["share"] for r in REGIONS])[:, None]

    def _shift(d, s):
        d = d.copy()
        if s <= 0: return d
        moved = s * d[:, PEAK].sum(axis=1)
        d[:, PEAK] *= (1 - s); d[:, OFFPEAK] += (moved / len(OFFPEAK))[:, None]
        return d

    def _risk(d, capacity, reserve):
        shares = np.array([r["share"] for r in REGIONS]); head = np.array([r["headroom"] for r in REGIONS])
        cap_r = capacity * (1 + reserve) * shares * head
        p_r = np.vstack([p_over((cap_r[i] - d[i]) / shares[i]) for i in range(len(REGIONS))])   # overload chance, region x hour
        nat = d.sum(axis=0); cap_n = capacity * (1 + reserve)
        return cap_r, p_r, nat, cap_n, p_over(cap_n - nat)

    def _status(p):
        return "overload" if p >= 0.5 else "risk" if p >= 0.15 else "watch" if p >= 0.03 else "safe"

    @app.post("/api/decision")
    def decision(body: Dict[str, Any]):
        try:
            T, H, month, dow, live = _context(body)
            capacity = float(body.get("capacity", reference["default_capacity_kw"]))
            s = float(body.get("shift_pct", 0)) / 100; tariff = float(body.get("tariff_pct", 0)) / 100; reserve = float(body.get("reserve_pct", 0)) / 100
            d0 = _regional_demand(body, T, H, month, dow, 0.0)
            d1 = _shift(_regional_demand(body, T, H, month, dow, tariff), s) if (s or tariff) else d0
            cap_r, p1, nat1, cap_n, pn1 = _risk(d1, capacity, reserve)
            _, p0, nat0, _, pn0 = _risk(d0, capacity, 0.0)
            hw = conf["levels"][str(body.get("confidence", 0.9))]["half_width_kw"]
            r1 = lambda a: np.round(a, 1).tolist(); r3 = lambda a: np.round(a, 3).tolist()
            regs = []
            for i, r in enumerate(REGIONS):
                wh = int(np.argmax(p1[i]))
                regs.append(dict(key=r["key"], city=r["city"], share=r["share"], capacity=round(float(cap_r[i]), 1), demand=r1(d1[i]), baseline=r1(d0[i]),
                                 p=r3(p1[i]), p_baseline=r3(p0[i]), temp=r1(T[i]), worst_hour=wh, worst_p=float(round(p1[i][wh], 3)),
                                 worst_p_baseline=float(round(p0[i].max(), 3)), status=_status(float(p1[i].max())), peak_kw=float(round(d1[i].max(), 1))))
            wn = int(np.argmax(pn1))
            return {"source": body.get("source", "scenario"), "live": ({"fetched_at": live["fetched_at"], "time": live["time"],
                                                                         "now": {k: v["now_temp"] for k, v in live["regions"].items()}} if live else None),
                    "month": month, "dow": dow, "confidence": body.get("confidence", 0.9), "half_width_kw": hw,
                    "national": dict(demand=r1(nat1), baseline=r1(nat0), lower=r1(nat1 - hw), upper=r1(nat1 + hw), p=r3(pn1), p_baseline=r3(pn0),
                                     capacity=round(cap_n, 1), capacity_baseline=round(capacity, 1), worst_hour=wn, worst_p=float(round(pn1[wn], 3)),
                                     worst_p_baseline=float(round(pn0.max(), 3)), peak_kw=float(round(nat1.max(), 1)), peak_kw_baseline=float(round(nat0.max(), 1))),
                    "regions": regs}
        except HTTPException: raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Decision failed: {e}")

    @app.post("/api/recommend")
    def recommend(body: Dict[str, Any]):
        """Cheapest lever mix (load shift + peak tariff) that pushes worst-hour national overload risk below the target."""
        try:
            T, H, month, dow, _ = _context(body)
            capacity = float(body.get("capacity", reference["default_capacity_kw"])); reserve = float(body.get("reserve_pct", 0)) / 100
            target = float(body.get("target", 0.05)); best = None; fallback = None
            for tariff in (0, 0.05, 0.10, 0.15, 0.20, 0.30):
                d_t = _regional_demand(body, T, H, month, dow, tariff)
                for s in np.arange(0, 0.31, 0.02):
                    d = _shift(d_t, float(s)); _, p_r, nat, cap_n, pn = _risk(d, capacity, reserve)
                    worst = float(pn.max()); cost = s * 100 + 0.6 * tariff * 100
                    n_reg = int((p_r.max(axis=1) >= 0.15).sum())
                    cand = dict(shift_pct=round(float(s) * 100, 1), tariff_pct=round(tariff * 100, 1), worst_p=round(worst, 3), regions_at_risk=n_reg, cost=cost)
                    if worst <= target and n_reg == 0 and (best is None or cost < best["cost"]): best = cand
                    if fallback is None or (worst, cost) < (fallback["worst_p"], fallback["cost"]): fallback = cand
            base = _risk(_regional_demand(body, T, H, month, dow, 0.0), capacity, reserve)
            return {"found": best is not None, "recommendation": best or fallback, "target": target,
                    "current_worst_p": float(base[4].max()), "current_regions_at_risk": int((base[1].max(axis=1) >= 0.15).sum())}
        except HTTPException: raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Recommend failed: {e}")

    @app.get("/api/performance")
    def performance():
        path = os.path.join(saved_dir, "performance.json")
        if not os.path.exists(path): raise HTTPException(status_code=404, detail="Run scripts/calibrate.py first")
        return json.load(open(path))
