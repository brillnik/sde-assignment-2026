#!/usr/bin/env bash
# ./run.sh <SIM_URL>  - starts the controller and runs until the scenario finishes. No manual steps.
# Runs natively with python3 (>=3.10) + requirements.txt. Docker is not required.
# State lives in $CTL_DB (default state/controller.db); delete it for a fresh world, keep it to resume after a crash.
set -euo pipefail
SIM_URL="${1:?usage: ./run.sh <SIM_URL>}"
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
exec "$PY" -m controller --url "$SIM_URL" --db "${CTL_DB:-state/controller.db}"
