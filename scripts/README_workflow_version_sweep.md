# Workflow Version Sweep

This sweep keeps the existing `A-F` flow intact and writes all new artifacts under `outputs/version_sweeps/`.

## What it does

1. Runs `backup/version_configs/generation_c_tune_v1.yaml` to `v4.yaml` with condition `C`
2. Reuses the existing generation, rule-based evaluation, and LLM judge scripts
3. Summarizes scores across versions
4. Selects the best `C` version by:
   - highest `LLM judge overall` mean
   - tie-breaker: highest `rule-based weighted_score` mean
5. Builds a derived config for `F` by copying the current `configs/generation.yaml` and replacing only `conditions.F.workflow` with the selected `C` workflow settings

## Commands

Run the `C` sweep:

```bash
bash scripts/run_c_version_sweep.sh
```

Run `F` with the selected best `C` workflow:

```bash
bash scripts/run_f_with_best_c_version.sh
```

Run both from Python:

```bash
python3 src/run_workflow_version_sweep.py run-all
```

Dry run only:

```bash
python3 src/run_workflow_version_sweep.py run-c-sweep --dry-run
python3 src/run_workflow_version_sweep.py run-best-f --dry-run
```

## Output layout

- `outputs/version_sweeps/c_v1`
- `outputs/version_sweeps/c_v2`
- `outputs/version_sweeps/c_v3`
- `outputs/version_sweeps/c_v4`
- `outputs/version_sweeps/c_version_summary.json`
- `outputs/version_sweeps/c_version_summary.csv`
- `outputs/version_sweeps/best_c_version.json`
- `outputs/version_sweeps/_generated/prompts_with_repair.yaml`
- `outputs/version_sweeps/_generated/generation_f_from_best_<version>.yaml`
- `outputs/version_sweeps/f_from_best_<version>`
