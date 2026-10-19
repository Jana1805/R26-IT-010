#!/usr/bin/env python3
"""Launcher for the four EDIS components: behaviour-intelligence (bi),
madushani_xai (xai), final_research (forecast), electricity-demand-sri-lanka (nn).

Starts each component's backend (uvicorn) and frontend (npm run dev) as
child processes and prints the four dashboard URLs once launched.

Ports (verified against each component's actual code, not its README):
    bi        backend 8001   frontend 3000
    xai       backend 8000   frontend 5173
    forecast  backend 8002   frontend 5175
    nn        backend 8003   frontend 5176

Every component runs on its OWN venv Python: behaviour-intelligence/.venv,
madushani_xai/venv, final_research/venv and electricity-demand-sri-lanka/.venv
(bi's and nn's are dot-prefixed). Their scikit-learn requirements conflict
with each other, so no single global Python can serve them all. bi used to
run on whichever Python launched this script; that broke once Python 3.14
(no uvicorn/fastapi) became the first "python" on PATH. The launcher itself
can run on any Python 3.

final_research MUST be started as "uvicorn app:app --port 8002". Its
app.py has a __main__ block that binds port 8000 directly, which would
collide with xai's backend -- never invoke it as "python app.py".

nn was moved from its original ports (8000, 5173) to (8003, 5176) to clear
that same collision with xai -- see electricity-demand-sri-lanka/frontend/
vite.config.js and api/core/config.py's ALLOWED_ORIGINS.

Does not modify anything inside behaviour-intelligence/, madushani_xai/,
final_research/, or electricity-demand-sri-lanka/. Pure standard library,
no third-party dependencies.

Usage:
    python start-all.py                    # start all four
    python start-all.py --only bi,xai      # start a subset
Ctrl+C stops every child process (and its full descendant tree) cleanly.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
IS_WINDOWS = sys.platform.startswith("win")

COMPONENTS = {
    "bi": {
        "label": "behaviour-intelligence (Thanujan)",
        "backend": {
            "name": "bi-backend",
            "cwd": ROOT / "behaviour-intelligence" / "backend",
            # NOTE: dot-prefixed .venv at the component root (Python 3.12,
            # behaviour-intelligence/requirements.txt pins), like nn's.
            "python": ROOT / "behaviour-intelligence" / ".venv" / "Scripts" / "python.exe",
            "args": ["-m", "uvicorn", "app.main:app", "--port", "8001"],
        },
        "frontend": {
            "name": "bi-frontend",
            "cwd": ROOT / "behaviour-intelligence" / "frontend",
            "command": "npm run dev",
        },
        "frontend_url": "http://localhost:3000",
    },
    "xai": {
        "label": "madushani_xai (Madushani)",
        "backend": {
            "name": "xai-backend",
            "cwd": ROOT / "madushani_xai" / "backend",
            "python": ROOT / "madushani_xai" / "venv" / "Scripts" / "python.exe",
            "args": ["-m", "uvicorn", "app:app", "--port", "8000"],
        },
        "frontend": {
            "name": "xai-frontend",
            "cwd": ROOT / "madushani_xai" / "frontend",
            "command": "npm run dev",
        },
        "frontend_url": "http://localhost:5173",
    },
    "forecast": {
        "label": "final_research (Dewmini)",
        "backend": {
            "name": "forecast-backend",
            "cwd": ROOT / "final_research" / "backend",
            "python": ROOT / "final_research" / "venv" / "Scripts" / "python.exe",
            # CRITICAL: must be "uvicorn app:app --port 8002" -- app.py's own
            # __main__ block binds 8000 and would collide with xai-backend.
            "args": ["-m", "uvicorn", "app:app", "--port", "8002"],
        },
        "frontend": {
            "name": "forecast-frontend",
            "cwd": ROOT / "final_research" / "frontend",
            "command": "npm run dev",
        },
        "frontend_url": "http://localhost:5175",
    },
    "nn": {
        "label": "electricity-demand-sri-lanka (Janahan)",
        "backend": {
            "name": "nn-backend",
            "cwd": ROOT / "electricity-demand-sri-lanka",
            # NOTE: this component's venv is .venv (dot-prefixed), unlike
            # madushani_xai/venv and final_research/venv.
            "python": ROOT / "electricity-demand-sri-lanka" / ".venv" / "Scripts" / "python.exe",
            "args": ["-m", "uvicorn", "api.main:app", "--port", "8003"],
        },
        "frontend": {
            "name": "nn-frontend",
            "cwd": ROOT / "electricity-demand-sri-lanka" / "frontend",
            "command": "npm run dev",
        },
        "frontend_url": "http://localhost:5176",
    },
}

processes = []  # list of (name, subprocess.Popen)


def start_backend(spec):
    name = spec["name"]
    cwd = spec["cwd"]
    python = spec["python"]

    if not cwd.is_dir():
        print(f"SKIP {name}: directory not found ({cwd})", flush=True)
        return
    if not python.is_file():
        print(f"SKIP {name}: python not found ({python})", flush=True)
        return

    cmd = f'"{python}" ' + " ".join(spec["args"])
    proc = subprocess.Popen(cmd, cwd=str(cwd), shell=True)
    processes.append((name, proc))
    print(f"START {name}: {cmd}  (cwd={cwd}, pid={proc.pid})", flush=True)


def start_frontend(spec):
    name = spec["name"]
    cwd = spec["cwd"]

    if not cwd.is_dir():
        print(f"SKIP {name}: directory not found ({cwd})", flush=True)
        return

    cmd = spec["command"]
    proc = subprocess.Popen(cmd, cwd=str(cwd), shell=True)
    processes.append((name, proc))
    print(f"START {name}: {cmd}  (cwd={cwd}, pid={proc.pid})", flush=True)


def stop_all():
    print("\nStopping all processes...", flush=True)
    for name, proc in processes:
        if proc.poll() is not None:
            continue  # already exited
        try:
            if IS_WINDOWS:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                proc.terminate()
            print(f"  stopped {name} (pid {proc.pid})", flush=True)
        except Exception as exc:
            print(f"  failed to stop {name}: {exc}", flush=True)
    print("Done.", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Launch EDIS components.")
    parser.add_argument(
        "--only",
        default="bi,xai,forecast,nn",
        help="Comma-separated subset to start: bi,xai,forecast,nn (default: all four)",
    )
    args = parser.parse_args()
    selected = [s.strip() for s in args.only.split(",") if s.strip()]

    unknown = [s for s in selected if s not in COMPONENTS]
    if unknown:
        print(f"Unknown component(s): {', '.join(unknown)} -- choices are bi, xai, forecast, nn")
        sys.exit(1)

    print("Starting components:", ", ".join(selected), flush=True)
    print(flush=True)

    for key in selected:
        spec = COMPONENTS[key]
        start_backend(spec["backend"])
        time.sleep(1.5)
        start_frontend(spec["frontend"])
        time.sleep(1.5)

    print(flush=True)
    print("Frontend URLs:", flush=True)
    for key in selected:
        spec = COMPONENTS[key]
        print(f"  {spec['label']:35s} {spec['frontend_url']}", flush=True)
    print(flush=True)
    print("Press Ctrl+C to stop everything.", flush=True)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        stop_all()


if __name__ == "__main__":
    main()
