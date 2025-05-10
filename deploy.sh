#!/bin/bash

# Exit on any error
set -euxo pipefail

python3.13 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install .

# remove old scheduler if it exists
pkill -f "job-board schedule" || echo "No previous scheduler to stop."
nohup job-board schedule &
