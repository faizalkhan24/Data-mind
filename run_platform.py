"""
DataMind Master Platform Runner
===============================
Starts and manages all 4 DataMind microservices concurrently:
- Prediction API:           http://127.0.0.1:8000
- Fleet Management API:     http://127.0.0.1:8001
- Streaming Ingestion:      http://127.0.0.1:8002
- Operations Console (UI):  http://127.0.0.1:8003
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import urllib.error


REPO_ROOT = Path(__file__).resolve().parent
PYTHON_EXE = sys.executable

SERVICES = [
    {
        "name": "DataMind.Prediction",
        "dir": REPO_ROOT / "services" / "DataMind.Prediction",
        "script": REPO_ROOT / "services" / "DataMind.Prediction" / "main.py",
        "port": 8000,
        "health_url": "http://127.0.0.1:8000/health",
        "docs_url": "http://127.0.0.1:8000/docs",
    },
    {
        "name": "DataMind.Api",
        "dir": REPO_ROOT / "services" / "DataMind.Api",
        "script": REPO_ROOT / "services" / "DataMind.Api" / "main.py",
        "port": 8001,
        "health_url": "http://127.0.0.1:8001/health",
        "docs_url": "http://127.0.0.1:8001/docs",
    },
    {
        "name": "DataMind.Ingestion",
        "dir": REPO_ROOT / "services" / "DataMind.Ingestion",
        "script": REPO_ROOT / "services" / "DataMind.Ingestion" / "main.py",
        "port": 8002,
        "health_url": "http://127.0.0.1:8002/health",
        "docs_url": "http://127.0.0.1:8002/docs",
    },
    {
        "name": "DataMind.Dashboard",
        "dir": REPO_ROOT / "services" / "DataMind.Dashboard",
        "script": REPO_ROOT / "services" / "DataMind.Dashboard" / "main.py",
        "port": 8003,
        "health_url": "http://127.0.0.1:8003/health",
        "docs_url": "http://127.0.0.1:8003/",
    },
]


def check_health(url: str, timeout: float = 2.0) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DataMind-HealthChecker"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def main() -> None:
    print("=" * 80)
    print("        DATAMIND PREDICTIVE INTELLIGENCE PLATFORM LAUNCHER")
    print("=" * 80)
    print(f"Working Directory : {REPO_ROOT}")
    print(f"Python Runtime    : {PYTHON_EXE}")
    print("-" * 80)

    processes: list[subprocess.Popen] = []
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)

    try:
        for svc in SERVICES:
            print(f"[*] Starting {svc['name']:<22} on port {svc['port']}...")
            svc_env = env.copy()
            # Insert service dir at front of PYTHONPATH
            svc_env["PYTHONPATH"] = f"{svc['dir']}{os.pathsep}{REPO_ROOT}"
            p = subprocess.Popen(
                [PYTHON_EXE, str(svc["script"])],
                cwd=str(svc["dir"]),
                env=svc_env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            processes.append(p)
            time.sleep(0.5)

        print("\n[*] Waiting for microservices to reach healthy state...")
        all_ready = False
        start_time = time.time()
        timeout = 25.0

        while time.time() - start_time < timeout:
            statuses = [check_health(svc["health_url"]) for svc in SERVICES]
            if all(statuses):
                all_ready = True
                break
            time.sleep(1.0)

        print("-" * 80)
        if all_ready:
            print("[+] ALL SERVICES ARE ONLINE AND OPERATIONAL!\n")
            print(f"  • Fleet Operations Dashboard : http://127.0.0.1:8003/")
            print(f"  • Prediction Inference API  : http://127.0.0.1:8000/docs")
            print(f"  • Fleet Persistence API     : http://127.0.0.1:8001/docs")
            print(f"  • Streaming Ingestion API   : http://127.0.0.1:8002/docs")
            print("-" * 80)
            print("Press Ctrl+C to stop all services.\n")
            while True:
                time.sleep(1.0)
        else:
            print("[!] Warning: Some services did not report healthy within timeout:")
            for svc in SERVICES:
                healthy = check_health(svc["health_url"])
                mark = "[OK]" if healthy else "[WAIT]"
                print(f"  {mark:<6} {svc['name']:<22} : {svc['health_url']}")
            print("\nKeeping running processes alive. Press Ctrl+C to terminate.")
            while True:
                time.sleep(1.0)

    except KeyboardInterrupt:
        print("\n[*] Terminating all DataMind microservices...")
    finally:
        for p in processes:
            try:
                p.terminate()
            except Exception:
                pass
        print("[+] All services shut down successfully.")


if __name__ == "__main__":
    main()
