#!/usr/bin/env python3
"""DataMind Unified Command-Line Interface (CLI) & Platform Orchestrator.

Provides single-command fleet lifecycle operations, service cluster orchestrations,
synthetic IoT simulation, database seeding, and diagnostic test runners.

Usage:
    python datamind.py version
    python datamind.py status
    python datamind.py test
    python datamind.py simulate --devices 20 --interval 2.0
    python datamind.py start --all
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Dict, List, Optional

PLATFORM_VERSION = "1.0.0.1"
DEFAULT_SERVICES = {
    "prediction": {"name": "DataMind.Prediction", "port": 8000, "entry": "services/DataMind.Prediction/main.py"},
    "api": {"name": "DataMind.Api", "port": 8001, "entry": "services/DataMind.Api/main.py"},
    "ingestion": {"name": "DataMind.Ingestion", "port": 8002, "entry": "services/DataMind.Ingestion/main.py"},
    "dashboard": {"name": "DataMind.Dashboard", "port": 8003, "entry": "services/DataMind.Dashboard/main.py"},
}


def cmd_version(args: argparse.Namespace) -> int:
    """Displays platform version and build metadata."""
    print("================================================================================")
    print(f"  DataMind Predictive Maintenance Platform  |  Version {PLATFORM_VERSION}")
    print("================================================================================")
    print("  Runtime Architecture : Python 3.11+ / FastAPI / XGBoost / asyncio")
    print("  Enterprise Compliance: [SECURITY-1..6] Verified, [VALIDATION-1..4] Active")
    print("  Repository URL       : https://github.com/faizalkhan24/Data-mind")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Probes status and readiness for all microservices in the cluster."""
    import urllib.request

    print("================================================================================")
    print(f"  DataMind Cluster Readiness Probe  (v{PLATFORM_VERSION})")
    print("================================================================================")
    print(f"{'SERVICE':<25} | {'PORT':<6} | {'STATUS':<12} | {'DETAILS'}")
    print("-" * 80)

    for key, svc in DEFAULT_SERVICES.items():
        url = f"http://localhost:{svc['port']}/health"
        status_str = "OFFLINE"
        detail = "Connection refused"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "DataMind-CLI"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    status_str = "HEALTHY"
                    data = json.loads(resp.read().decode("utf-8"))
                    detail = f"v{data.get('version', PLATFORM_VERSION)}"
                else:
                    status_str = f"HTTP {resp.status}"
        except Exception:
            pass

        print(f"{svc['name']:<25} | {svc['port']:<6} | {status_str:<12} | {detail}")

    print("================================================================================")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    """Launches terminal-based real-time IoT fleet telemetry simulation."""
    from services.simulator.fleet_simulator import FleetSimulator

    dev_count = getattr(args, "devices", 20)
    interval = getattr(args, "interval", 2.0)
    target_url = getattr(args, "url", "http://localhost:8002")

    print("================================================================================")
    print(f"  DataMind Live IoT Fleet Simulator  |  {dev_count} Devices  |  Interval: {interval}s")
    print(f"  Target Ingestion URL: {target_url}")
    print("  Press Ctrl+C to stop simulation.")
    print("================================================================================")

    sim = FleetSimulator(
        device_count=dev_count,
        tick_interval_seconds=interval,
        target_ingestion_url=target_url,
    )

    tick = 0
    try:
        while True:
            t0 = time.perf_counter()
            readings = sim.tick_once()
            dt_ms = (time.perf_counter() - t0) * 1000.0
            tick += 1

            anomalies = [r for r in readings if r["temperature"] > 70.0 or r["voltage"] < 3.2 or r["error_count"] > 0]
            status_tag = f"[{len(anomalies)} ANOMALIES]" if anomalies else "[NOMINAL]"

            print(
                f"Tick #{tick:04d} | Dispatched {len(readings)} readings in {dt_ms:.2f}ms | "
                f"Total Sent: {sim.total_payloads_sent:05d} {status_tag}"
            )
            for a in anomalies[:2]:
                print(f"   -> Anomaly on {a['device_id']}: Temp={a['temperature']}°C, Volt={a['voltage']}V, Errors={a['error_count']}")

            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[INFO] Simulation terminated by user. Total events dispatched:", sim.total_payloads_sent)
        return 0


def cmd_test(args: argparse.Namespace) -> int:
    """Executes all unit and integration test suites."""
    print("================================================================================")
    print(f"  Executing DataMind Comprehensive Test Suite (v{PLATFORM_VERSION})")
    print("================================================================================")

    python_exe = sys.executable
    test_files = [
        "tests/test_security_and_validation.py",
        "tests/services/test_fleet_api.py",
        "tests/services/test_prediction_api.py",
        "tests/services/test_ingestion_stream.py",
        "tests/services/test_dashboard.py",
        "tests/services/test_simulator.py",
        "tests/test_end_to_end_integration.py",
    ]

    all_passed = True
    for t_file in test_files:
        cmd = [python_exe, "-m", "unittest", t_file]
        print(f"\n[RUNNING] {t_file}...")
        res = subprocess.run(cmd, cwd=str(Path(__file__).resolve().parent))
        if res.returncode != 0:
            all_passed = False
            print(f"[FAIL] {t_file} failed with exit code {res.returncode}")
        else:
            print(f"[PASS] {t_file}")

    print("\n" + "=" * 80)
    if all_passed:
        print("  ALL TEST SUITES PASSED (100% GREEN)")
    else:
        print("  TEST SUITE REPORTED FAILURES")
    print("=" * 80)
    return 0 if all_passed else 1


def cmd_start(args: argparse.Namespace) -> int:
    """Orchestrates and launches DataMind services cluster."""
    print("================================================================================")
    print(f"  Starting DataMind Microservices Cluster (v{PLATFORM_VERSION})")
    print("================================================================================")

    python_exe = sys.executable
    repo_root = Path(__file__).resolve().parent
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)

    processes = {}
    service_keys = list(DEFAULT_SERVICES.keys()) if args.all else []
    if args.dashboard: service_keys.append("dashboard")
    if args.api: service_keys.append("api")
    if args.prediction: service_keys.append("prediction")
    if args.ingestion: service_keys.append("ingestion")

    if not service_keys:
        service_keys = list(DEFAULT_SERVICES.keys())

    print(f"Launching services: {', '.join(service_keys)}")
    try:
        for sk in service_keys:
            svc = DEFAULT_SERVICES[sk]
            script_path = repo_root / svc["entry"]
            print(f"Starting {svc['name']} on http://localhost:{svc['port']}...")
            proc = subprocess.Popen([python_exe, str(script_path)], env=env)
            processes[sk] = proc

        print("\nAll cluster processes initiated.")
        print("Access Fleet Console: http://localhost:8003")
        print("Press Ctrl+C to terminate all services.\n")

        if getattr(args, "browser", False):
            import threading
            def _open_ui():
                time.sleep(2.0)
                try:
                    import webbrowser
                    webbrowser.open("http://localhost:8003")
                except Exception:
                    pass
            threading.Thread(target=_open_ui, daemon=True).start()

        while True:
            time.sleep(1.0)
            for sk, p in list(processes.items()):
                ret = p.poll()
                if ret is not None:
                    print(f"[WARNING] Service {sk} exited with code {ret}")
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down cluster services...")
    finally:
        for sk, p in processes.items():
            print(f"Terminating {sk}...")
            p.terminate()
            try:
                p.wait(timeout=2.0)
            except Exception:
                p.kill()
        print("Cluster shutdown complete.")
    return 0


def main() -> int:
    """CLI Argument Parser & Dispatcher."""
    parser = argparse.ArgumentParser(description=f"DataMind Unified Operations CLI (v{PLATFORM_VERSION})")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # version
    subparsers.add_parser("version", help="Print version and build details")

    # status
    subparsers.add_parser("status", help="Check cluster readiness status")

    # test
    subparsers.add_parser("test", help="Run comprehensive unit and integration test suite")

    # simulate
    sim_parser = subparsers.add_parser("simulate", help="Run real-time IoT fleet telemetry generator")
    sim_parser.add_argument("--devices", type=int, default=20, help="Number of IoT devices to simulate")
    sim_parser.add_argument("--interval", type=float, default=2.0, help="Tick interval in seconds")
    sim_parser.add_argument("--url", type=str, default="http://localhost:8002", help="Ingestion service target URL")

    # start
    start_parser = subparsers.add_parser("start", help="Start DataMind cluster services")
    start_parser.add_argument("--all", action="store_true", default=True, help="Start all 4 microservices")
    start_parser.add_argument("--dashboard", action="store_true", help="Start Dashboard service")
    start_parser.add_argument("--api", action="store_true", help="Start Core Api service")
    start_parser.add_argument("--prediction", action="store_true", help="Start Prediction service")
    start_parser.add_argument("--ingestion", action="store_true", help="Start Ingestion service")
    start_parser.add_argument("--browser", dest="browser", action="store_true", default=False, help="Automatically open browser to Dashboard URL")
    start_parser.add_argument("--no-browser", dest="browser", action="store_false", help="Do not open browser")

    args = parser.parse_args()

    if args.command == "version":
        return cmd_version(args)
    elif args.command == "status":
        return cmd_status(args)
    elif args.command == "simulate":
        return cmd_simulate(args)
    elif args.command == "test":
        return cmd_test(args)
    elif args.command == "start":
        return cmd_start(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
