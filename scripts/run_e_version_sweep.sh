#!/usr/bin/env bash
set -euo pipefail

python3 src/run_workflow_version_sweep.py run-e-sweep "$@"
