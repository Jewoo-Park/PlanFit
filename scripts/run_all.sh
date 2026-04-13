#!/usr/bin/env bash
set -euo pipefail

python3 src/load_personas.py
python3 src/generate_condition_a.py
python3 src/generate_condition_b.py
python3 src/generate_condition_c.py
python3 src/generate_condition_d.py
python3 src/generate_condition_e.py
python3 src/generate_condition_f.py
