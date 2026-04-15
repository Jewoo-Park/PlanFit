from __future__ import annotations

import argparse
import csv
import json
import shlex
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List

import yaml

from utils import load_jsonl, load_yaml, resolve_path, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPAIR_PROMPT_PATH = Path("backup/methods/01_repair_loop_core/refs/workflow_repair_planner.txt")
SUMMARY_JSON_NAME = "c_version_summary.json"
SUMMARY_CSV_NAME = "c_version_summary.csv"
BEST_JSON_NAME = "best_c_version.json"


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_yaml(path: Path, payload: Dict[str, Any]) -> None:
    _ensure_parent(path)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _run_command(cmd: List[str], *, dry_run: bool) -> None:
    pretty = " ".join(shlex.quote(part) for part in cmd)
    print(f"$ {pretty}")
    if dry_run:
        return
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)


def _version_configs(version_glob: str) -> List[Path]:
    root_pattern = resolve_path(version_glob)
    matches = sorted(root_pattern.parent.glob(root_pattern.name))
    if not matches:
        raise FileNotFoundError(f"No version configs matched {version_glob!r}")
    return matches


def _ensure_prompts_with_repair(
    *,
    prompts_config_path: str,
    output_root: Path,
) -> Path:
    prompts_cfg = load_yaml(prompts_config_path)
    prompt_files = dict(prompts_cfg.get("prompt_files", {}))
    repair_prompt = resolve_path(str(REPAIR_PROMPT_PATH))
    if not repair_prompt.exists():
        raise FileNotFoundError(f"Missing repair prompt at {repair_prompt}")
    prompt_files["workflow_repair_planner"] = str(REPAIR_PROMPT_PATH)
    derived_cfg = {"prompt_files": prompt_files}
    target = output_root / "_generated" / "prompts_with_repair.yaml"
    _write_yaml(target, derived_cfg)
    return target


def _run_generation_and_evals(
    *,
    condition: str,
    generation_config: Path,
    prompts_config: Path,
    models_config: str,
    evaluation_config: str,
    personas_path: str,
    output_dir: Path,
    dry_run: bool,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    common = [
        sys.executable,
        "src/generate.py",
        "--condition",
        condition,
        "--generation-config",
        str(generation_config),
        "--prompts-config",
        str(prompts_config),
        "--models-config",
        models_config,
        "--input",
        personas_path,
        "--output-dir",
        str(output_dir),
    ]
    _run_command(common, dry_run=dry_run)

    _run_command(
        [
            sys.executable,
            "src/evaluate_rule_based.py",
            "--outputs",
            str(output_dir / "results.jsonl"),
            "--personas",
            personas_path,
            "--evaluation-config",
            evaluation_config,
            "--output-path",
            str(output_dir / "evaluation_rule_based.jsonl"),
        ],
        dry_run=dry_run,
    )

    _run_command(
        [
            sys.executable,
            "src/evaluate_llm_judge.py",
            "--outputs",
            str(output_dir / "results.jsonl"),
            "--personas",
            personas_path,
            "--models-config",
            models_config,
            "--evaluation-config",
            evaluation_config,
            "--output-path",
            str(output_dir / "evaluation_llm_judge.jsonl"),
        ],
        dry_run=dry_run,
    )


def _mean_or_none(values: Iterable[float]) -> float | None:
    materialized = list(values)
    if not materialized:
        return None
    return float(mean(materialized))


def _summarize_output(version_label: str, version_config: Path, output_dir: Path) -> Dict[str, Any]:
    rule_rows = load_jsonl(str(output_dir / "evaluation_rule_based.jsonl"))
    judge_rows = load_jsonl(str(output_dir / "evaluation_llm_judge.jsonl"))
    if not rule_rows or not judge_rows:
        raise FileNotFoundError(f"Missing evaluation outputs under {output_dir}")

    llm_metric_names = [
        "goal_alignment",
        "constraint_adherence",
        "safety",
        "tradeoff_handling",
        "progression_coherence",
        "overall",
    ]
    llm_averages: Dict[str, float | None] = {
        metric: _mean_or_none(
            row["judgment"].get(metric)
            for row in judge_rows
            if row.get("judgment", {}).get(metric) is not None
        )
        for metric in llm_metric_names
    }

    rule_average = _mean_or_none(row.get("weighted_score") for row in rule_rows if row.get("weighted_score") is not None)
    return {
        "version": version_label,
        "generation_config": str(version_config),
        "output_dir": str(output_dir),
        "counts": {
            "generation": len(load_jsonl(str(output_dir / "results.jsonl"))),
            "rule_based": len(rule_rows),
            "llm_judge": len(judge_rows),
        },
        "rule_based": {
            "weighted_mean": rule_average,
        },
        "llm_judge": {
            "metric_means": llm_averages,
        },
    }


def _write_summary_files(output_root: Path, summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
    ordered = sorted(
        summaries,
        key=lambda item: (
            -(item["llm_judge"]["metric_means"]["overall"] or float("-inf")),
            -(item["rule_based"]["weighted_mean"] or float("-inf")),
            item["version"],
        ),
    )
    best = ordered[0]

    summary_payload = {
        "selection_rule": {
            "primary": "highest llm_judge.metric_means.overall",
            "tie_breaker": "highest rule_based.weighted_mean",
        },
        "versions": summaries,
        "best_version": best["version"],
    }
    write_json(output_root / SUMMARY_JSON_NAME, summary_payload)
    write_json(output_root / BEST_JSON_NAME, best)

    csv_path = output_root / SUMMARY_CSV_NAME
    _ensure_parent(csv_path)
    fieldnames = [
        "version",
        "generation_config",
        "output_dir",
        "generation_count",
        "rule_based_count",
        "llm_judge_count",
        "rule_weighted_mean",
        "llm_goal_alignment_mean",
        "llm_constraint_adherence_mean",
        "llm_safety_mean",
        "llm_tradeoff_handling_mean",
        "llm_progression_coherence_mean",
        "llm_overall_mean",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in summaries:
            metrics = item["llm_judge"]["metric_means"]
            writer.writerow(
                {
                    "version": item["version"],
                    "generation_config": item["generation_config"],
                    "output_dir": item["output_dir"],
                    "generation_count": item["counts"]["generation"],
                    "rule_based_count": item["counts"]["rule_based"],
                    "llm_judge_count": item["counts"]["llm_judge"],
                    "rule_weighted_mean": item["rule_based"]["weighted_mean"],
                    "llm_goal_alignment_mean": metrics["goal_alignment"],
                    "llm_constraint_adherence_mean": metrics["constraint_adherence"],
                    "llm_safety_mean": metrics["safety"],
                    "llm_tradeoff_handling_mean": metrics["tradeoff_handling"],
                    "llm_progression_coherence_mean": metrics["progression_coherence"],
                    "llm_overall_mean": metrics["overall"],
                }
            )
    return best


def _derived_f_generation_config(
    *,
    base_generation_config: str,
    best_c_generation_config: Path,
    best_version_label: str,
    output_root: Path,
) -> Path:
    base_cfg = load_yaml(base_generation_config)
    best_cfg = load_yaml(str(best_c_generation_config))
    derived_cfg = deepcopy(base_cfg)

    best_c_workflow = deepcopy(best_cfg["conditions"]["C"].get("workflow", {}))
    derived_cfg["conditions"]["F"]["workflow"] = best_c_workflow
    derived_cfg["conditions"]["F"]["system_type"] = (
        f"{derived_cfg['conditions']['F'].get('system_type', 'langgraph_workflow_planner')}_best_{best_version_label}"
    )

    target = output_root / "_generated" / f"generation_f_from_best_{best_version_label}.yaml"
    _write_yaml(target, derived_cfg)
    return target


def run_c_sweep(args: argparse.Namespace) -> None:
    output_root = resolve_path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    prompts_with_repair = _ensure_prompts_with_repair(
        prompts_config_path=args.prompts_config,
        output_root=output_root,
    )

    summaries: List[Dict[str, Any]] = []
    for config_path in _version_configs(args.version_glob):
        version_label = config_path.stem.replace("generation_c_tune_", "")
        output_dir = output_root / f"c_{version_label}"
        _run_generation_and_evals(
            condition="C",
            generation_config=config_path,
            prompts_config=prompts_with_repair,
            models_config=args.models_config,
            evaluation_config=args.evaluation_config,
            personas_path=args.personas,
            output_dir=output_dir,
            dry_run=args.dry_run,
        )
        if not args.dry_run:
            summaries.append(_summarize_output(version_label, config_path, output_dir))

    if args.dry_run:
        print("Dry run complete. No generation or evaluation jobs were executed.")
        return

    best = _write_summary_files(output_root, summaries)
    print(
        "Best C version:",
        best["version"],
        "llm_overall=",
        best["llm_judge"]["metric_means"]["overall"],
        "rule_weighted=",
        best["rule_based"]["weighted_mean"],
    )


def run_best_f(args: argparse.Namespace) -> None:
    output_root = resolve_path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    prompts_with_repair = _ensure_prompts_with_repair(
        prompts_config_path=args.prompts_config,
        output_root=output_root,
    )

    if args.best_c_config:
        best_config_path = resolve_path(args.best_c_config)
        best_version_label = best_config_path.stem.replace("generation_c_tune_", "")
    else:
        best_summary_path = output_root / BEST_JSON_NAME
        if not best_summary_path.exists():
            raise FileNotFoundError(
                f"Missing {best_summary_path}. Run the C sweep first or pass --best-c-config."
            )
        best_summary = json.loads(best_summary_path.read_text(encoding="utf-8"))
        best_config_path = resolve_path(best_summary["generation_config"])
        best_version_label = str(best_summary["version"])

    derived_config = _derived_f_generation_config(
        base_generation_config=args.base_generation_config,
        best_c_generation_config=best_config_path,
        best_version_label=best_version_label,
        output_root=output_root,
    )
    output_dir = output_root / f"f_from_best_{best_version_label}"
    _run_generation_and_evals(
        condition="F",
        generation_config=derived_config,
        prompts_config=prompts_with_repair,
        models_config=args.models_config,
        evaluation_config=args.evaluation_config,
        personas_path=args.personas,
        output_dir=output_dir,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print("Dry run complete. Derived F config was prepared but not executed.")
        return

    summary = {
        "source_best_c_version": best_version_label,
        "derived_generation_config": str(derived_config),
        "output_dir": str(output_dir),
        "rule_based": _summarize_output(f"f_from_best_{best_version_label}", derived_config, output_dir)["rule_based"],
        "llm_judge": _summarize_output(f"f_from_best_{best_version_label}", derived_config, output_dir)["llm_judge"],
    }
    write_json(output_root / f"f_from_best_{best_version_label}_summary.json", summary)
    print(f"Finished F rerun with best C version {best_version_label}")


def run_all(args: argparse.Namespace) -> None:
    run_c_sweep(args)
    if args.dry_run:
        return
    run_best_f(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run C workflow-version sweeps and rerun F with the best C workflow knobs."
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--personas", default="data/processed/personas_normalized.jsonl")
    common.add_argument("--models-config", default="configs/models.yaml")
    common.add_argument("--prompts-config", default="configs/prompts.yaml")
    common.add_argument("--evaluation-config", default="configs/evaluation.yaml")
    common.add_argument("--base-generation-config", default="configs/generation.yaml")
    common.add_argument(
        "--version-glob",
        default="backup/version_configs/generation_c_tune_v*.yaml",
        help="Glob for C version configs.",
    )
    common.add_argument(
        "--output-root",
        default="outputs/version_sweeps",
        help="Dedicated output root for sweep artifacts.",
    )
    common.add_argument(
        "--best-c-config",
        default=None,
        help="Optional explicit C version config to use when running F.",
    )
    common.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands and prepare derived configs without running heavy generation/evaluation.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run-c-sweep", parents=[common], help="Run C v1-v4 generation and evaluation.")
    subparsers.add_parser("run-best-f", parents=[common], help="Run F using the best C workflow knobs.")
    subparsers.add_parser("run-all", parents=[common], help="Run the C sweep, then run F from the selected best C version.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "run-c-sweep":
        run_c_sweep(args)
    elif args.command == "run-best-f":
        run_best_f(args)
    else:
        run_all(args)


if __name__ == "__main__":
    main()
