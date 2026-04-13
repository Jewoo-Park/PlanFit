#!/usr/bin/env bash
set -euo pipefail

python3 src/load_personas.py
python3 src/generate_condition_e.py
