#!/usr/bin/env bash
# DataMind One-Click Startup Script for Linux / macOS / WSL
# Usage: ./start_datamind.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH}"

if [ -f "${SCRIPT_DIR}/.venv/bin/python" ]; then
    PYTHON_EXE="${SCRIPT_DIR}/.venv/bin/python"
    echo "[OK] Using virtual environment Python: ${PYTHON_EXE}"
else
    PYTHON_EXE="python3"
    echo "[INFO] Using system Python: ${PYTHON_EXE}"
fi

echo "================================================================================"
echo "  Starting DataMind Predictive Intelligence Platform (v1.0.0.1)"
echo "================================================================================"

${PYTHON_EXE} "${SCRIPT_DIR}/datamind.py" version

echo ""
echo "Launching all cluster microservices (Dashboard, Api, Prediction, Ingestion)..."
${PYTHON_EXE} "${SCRIPT_DIR}/datamind.py" start --all --browser
