# Workflow Version Sweep

This sweep keeps the existing `A-F` flow intact and writes all new artifacts under `outputs/version_sweeps/`.

## What it does

1. Runs `backup/version_configs/generation_e_tune_v1.yaml` to `v4.yaml` with condition `E`
2. Reuses the existing generation and LLM judge scripts
3. Summarizes scores across versions
4. Selects the best `E` version by:
   - highest `LLM judge overall` mean
   - tie-breaker: stable version label ordering
5. Builds a derived config for `F` by copying the current `configs/generation.yaml` and replacing only `conditions.F.workflow` with the selected `E` workflow settings

## Commands

Run the `E` sweep:

```bash
bash scripts/run_e_version_sweep.sh
```

Run `F` with the selected best `E` workflow:

```bash
bash scripts/run_f_with_best_e_version.sh
```

Run both from Python:

```bash
python3 src/run_workflow_version_sweep.py run-all
```

Dry run only:

```bash
python3 src/run_workflow_version_sweep.py run-e-sweep --dry-run
python3 src/run_workflow_version_sweep.py run-best-f --dry-run
```

## Output layout

- `outputs/version_sweeps/e_v1`
- `outputs/version_sweeps/e_v2`
- `outputs/version_sweeps/e_v3`
- `outputs/version_sweeps/e_v4`
- `outputs/version_sweeps/e_version_summary.json`
- `outputs/version_sweeps/e_version_summary.csv`
- `outputs/version_sweeps/best_e_version.json`
- `outputs/version_sweeps/_generated/prompts_with_repair.yaml`
- `outputs/version_sweeps/_generated/generation_f_from_best_<version>.yaml`
- `outputs/version_sweeps/f_from_best_<version>`
