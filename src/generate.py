import argparse
from typing import Any, Dict, List, Optional

from tqdm import tqdm

from postprocess import build_output_record
from prompt_builder import build_prompt
from schema import GenerationMetadata
from utils import (
    build_generator,
    load_jsonl,
    load_yaml,
    save_condition_outputs,
    save_run_info,
    set_seed,
    utc_now_iso,
)
from workflow import DynamicMultiAgentWorkflowRunner, LangGraphWorkflowRunner


CONDITION_OUTPUT_DEFAULTS = {
    "A": "outputs/condition_a",
    "B": "outputs/condition_b",
    "C": "outputs/condition_c",
    "D": "outputs/condition_d",
    "E": "outputs/condition_e",
    "F": "outputs/condition_f",
    "G": "outputs/condition_g",
    "H": "outputs/condition_h",
    "I": "outputs/condition_i",
    "J": "outputs/condition_j",
    "K": "outputs/condition_k",
    "L": "outputs/condition_l",
}


def _model_cfg(models_data: Dict[str, Any], alias: str) -> Dict[str, Any]:
    try:
        return models_data["models"][alias]
    except KeyError as exc:
        raise KeyError(f"Unknown model alias {alias!r} in configs/models.yaml") from exc


def _metadata_extra_for_model(
    model_cfg: Dict[str, Any], prompt_files: Dict[str, str]
) -> Dict[str, Any]:
    extra: Dict[str, Any] = {"prompt_files": prompt_files}
    rev = model_cfg.get("revision") or model_cfg.get("hf_revision")
    if rev not in (None, "", "null"):
        extra["hf_revision"] = str(rev)
    return extra


def _metadata_base(default_gen: Dict[str, Any], generated_at: str) -> GenerationMetadata:
    return GenerationMetadata(
        prompt_version=str(default_gen["prompt_version"]),
        temperature=float(default_gen["temperature"]),
        top_p=float(default_gen["top_p"]),
        max_tokens=int(default_gen["max_tokens"]),
        seed=int(default_gen["seed"]),
        generated_at=generated_at,
    )


def run_direct_condition(
    condition: str,
    personas: List[Dict[str, Any]],
    models_data: Dict[str, Any],
    prompts_cfg: Dict[str, Any],
    generation_cfg: Dict[str, Any],
    default_gen: Dict[str, Any],
    generated_at: str,
) -> List[Dict[str, Any]]:
    cond_cfg = generation_cfg["conditions"][condition]
    alias = cond_cfg["model_alias"]
    model_cfg = _model_cfg(models_data, alias)
    generator = build_generator(model_cfg)

    prompt_key = cond_cfg.get("prompt_key", condition)
    prompt_path = prompts_cfg["prompt_files"][prompt_key]
    meta_base = _metadata_base(default_gen, generated_at)
    extra = _metadata_extra_for_model(model_cfg, {"main": prompt_path})
    extra["system_type"] = str(cond_cfg.get("system_type", "direct"))

    records: List[Dict[str, Any]] = []
    for persona in tqdm(personas, desc=f"Condition {condition}"):
        prompt = build_prompt(prompt_key, persona, prompts_cfg)
        output_text = generator.generate(prompt, default_gen)
        records.append(
            build_output_record(
                persona=persona,
                condition=condition,
                model_name=model_cfg["display_name"],
                model_path_or_name=str(model_cfg["path_or_name"]),
                solution_raw_text=output_text,
                metadata=meta_base,
                metadata_extra=extra,
            )
        )
    return records


def run_workflow_condition(
    condition: str,
    personas: List[Dict[str, Any]],
    models_data: Dict[str, Any],
    prompts_cfg: Dict[str, Any],
    generation_cfg: Dict[str, Any],
    default_gen: Dict[str, Any],
    generated_at: str,
) -> List[Dict[str, Any]]:
    cond_cfg = generation_cfg["conditions"][condition]
    alias = cond_cfg["workflow_model_alias"]
    model_cfg = _model_cfg(models_data, alias)
    generator = build_generator(model_cfg)
    meta_base = _metadata_base(default_gen, generated_at)
    runner_type = cond_cfg.get("runner", "workflow")

    if runner_type == "dynamic_workflow":
        workflow_runner = DynamicMultiAgentWorkflowRunner(
            generator=generator,
            prompts_cfg=prompts_cfg,
            gen_cfg=default_gen,
            workflow_cfg=cond_cfg.get("workflow"),
        )
    else:
        workflow_runner = LangGraphWorkflowRunner(
            generator=generator,
            prompts_cfg=prompts_cfg,
            gen_cfg=default_gen,
            workflow_cfg=cond_cfg.get("workflow"),
        )
    workflow_prompt_files = {
        prompt_key: prompts_cfg["prompt_files"][prompt_key]
        for prompt_key in workflow_runner.prompt_keys.values()
    }
    metadata_base = _metadata_extra_for_model(model_cfg, workflow_prompt_files)
    metadata_base["system_type"] = str(cond_cfg.get("system_type", "langgraph_workflow"))
    metadata_base["workflow_nodes"] = workflow_runner.node_order

    records: List[Dict[str, Any]] = []
    for persona in tqdm(personas, desc=f"Condition {condition} (workflow)"):
        workflow_result = workflow_runner.run(persona)
        metadata_extra = dict(metadata_base)
        metadata_extra.update(
            {
                "workflow_trace": workflow_result["workflow_trace"],
                "model_calls": workflow_result["model_calls"],
                "checker_fail_count": workflow_result["checker_fail_count"],
                "revision_loops": workflow_result["revision_loops"],
                "caught_by_node": workflow_result["caught_by_node"],
                "remaining_fail_nodes": workflow_result.get("remaining_fail_nodes", []),
                "profile_summary": workflow_result["profile_summary"],
                "goal_strategy": workflow_result["goal_strategy"],
                "safety_review": workflow_result["safety_review"],
                "constraint_review": workflow_result["constraint_review"],
                "tradeoff_review": workflow_result["tradeoff_review"],
            }
        )
        if "initial_fail_nodes" in workflow_result:
            metadata_extra["initial_fail_nodes"] = workflow_result["initial_fail_nodes"]
        if "routing_trace" in workflow_result:
            metadata_extra["routing_trace"] = workflow_result["routing_trace"]
        if "fixer_calls" in workflow_result:
            metadata_extra["fixer_calls"] = workflow_result["fixer_calls"]
        if "fixers_triggered" in workflow_result:
            metadata_extra["fixers_triggered"] = workflow_result["fixers_triggered"]
        records.append(
            build_output_record(
                persona=persona,
                condition=condition,
                model_name=model_cfg["display_name"],
                model_path_or_name=str(model_cfg["path_or_name"]),
                solution_raw_text=workflow_result["final_plan"],
                metadata=meta_base,
                original_plan=workflow_result.get("initial_draft_plan", workflow_result["draft_plan"]),
                revised_plan=workflow_result["final_plan"],
                metadata_extra=metadata_extra,
            )
        )
    return records


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Generate training plans for conditions A–L.")
    parser.add_argument(
        "--condition",
        choices=["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"],
        required=True,
    )
    parser.add_argument("--input", default="data/processed/personas_normalized.jsonl")
    parser.add_argument("--models-config", default="configs/models.yaml")
    parser.add_argument("--prompts-config", default="configs/prompts.yaml")
    parser.add_argument("--generation-config", default="configs/generation.yaml")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument(
        "--deterministic-cuda",
        action="store_true",
        help="Enable cudnn deterministic mode (slower; does not fully fix sampling randomness).",
    )
    args = parser.parse_args(argv)

    output_dir = args.output_dir or CONDITION_OUTPUT_DEFAULTS[args.condition]

    personas = load_jsonl(args.input)
    models_data = load_yaml(args.models_config)
    prompts_cfg = load_yaml(args.prompts_config)
    generation_cfg = load_yaml(args.generation_config)
    default_gen = generation_cfg["default"]

    if "conditions" not in generation_cfg or args.condition not in generation_cfg["conditions"]:
        raise KeyError(f"configs/generation.yaml must define conditions.{args.condition}")

    set_seed(int(default_gen["seed"]), deterministic_cuda=args.deterministic_cuda)
    generated_at = utc_now_iso()

    save_run_info(
        output_dir,
        condition=args.condition,
        generation_config_path=args.generation_config,
        models_config_path=args.models_config,
        prompts_config_path=args.prompts_config,
        default_gen=default_gen,
    )

    runner_type = generation_cfg["conditions"][args.condition].get("runner", "direct")
    if runner_type in {"workflow", "dynamic_workflow"}:
        records = run_workflow_condition(
            args.condition,
            personas,
            models_data,
            prompts_cfg,
            generation_cfg,
            default_gen,
            generated_at,
        )
    else:
        records = run_direct_condition(
            args.condition,
            personas,
            models_data,
            prompts_cfg,
            generation_cfg,
            default_gen,
            generated_at,
        )

    save_condition_outputs(output_dir, records)
    print(f"Saved {len(records)} records to {output_dir}")


if __name__ == "__main__":
    main()
