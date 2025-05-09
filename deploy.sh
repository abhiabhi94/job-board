#!/bin/bash

# Exit on any error
set -euxo pipefail

# Create and activate virtual environment
python3.13 -m venv .venv
. .venv/bin/activate

pip install --upgrade pip setuptools wheel
pip install .

nohup job-board schedule &
