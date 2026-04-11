import argparse
from typing import Any, Dict, List, Optional, Tuple

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


CONDITION_OUTPUT_DEFAULTS = {
    "A": "outputs/condition_a",
    "B": "outputs/condition_b",
    "C": "outputs/condition_c",
    "D": "outputs/condition_d",
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


def run_condition_abd(
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

    prompt_key = condition
    prompt_path = prompts_cfg["prompt_files"][prompt_key]
    meta_base = GenerationMetadata(
        prompt_version=str(default_gen["prompt_version"]),
        temperature=float(default_gen["temperature"]),
        top_p=float(default_gen["top_p"]),
        max_tokens=int(default_gen["max_tokens"]),
        seed=int(default_gen["seed"]),
        generated_at=generated_at,
    )
    extra = _metadata_extra_for_model(model_cfg, {"main": prompt_path})

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


def run_condition_c(
    personas: List[Dict[str, Any]],
    models_data: Dict[str, Any],
    prompts_cfg: Dict[str, Any],
    generation_cfg: Dict[str, Any],
    default_gen: Dict[str, Any],
    generated_at: str,
) -> List[Dict[str, Any]]:
    cond_cfg = generation_cfg["conditions"]["C"]
    planner_alias = cond_cfg["planner_model_alias"]
    reviser_alias = cond_cfg["reviser_model_alias"]
    planner_cfg = _model_cfg(models_data, planner_alias)
    reviser_cfg = _model_cfg(models_data, reviser_alias)

    planner_prompt_path = prompts_cfg["prompt_files"]["A"]
    reviser_prompt_path = prompts_cfg["prompt_files"]["C"]

    meta_base = GenerationMetadata(
        prompt_version=str(default_gen["prompt_version"]),
        temperature=float(default_gen["temperature"]),
        top_p=float(default_gen["top_p"]),
        max_tokens=int(default_gen["max_tokens"]),
        seed=int(default_gen["seed"]),
        generated_at=generated_at,
    )

    small_generator = build_generator(planner_cfg)
    originals: List[Tuple[Dict[str, Any], str]] = []
    for persona in tqdm(personas, desc="Condition C (planner)"):
        original_prompt = build_prompt("A", persona, prompts_cfg)
        original_plan = small_generator.generate(original_prompt, default_gen)
        originals.append((persona, original_plan))
    small_generator.unload()

    strong_generator = build_generator(reviser_cfg)
    records: List[Dict[str, Any]] = []
    metadata_extra: Dict[str, Any] = {
        "prompt_files": {"planner": planner_prompt_path, "reviser": reviser_prompt_path},
        "planner_model_path_or_name": str(planner_cfg["path_or_name"]),
        "reviser_model_path_or_name": str(reviser_cfg["path_or_name"]),
    }
    prev = planner_cfg.get("revision") or planner_cfg.get("hf_revision")
    if prev not in (None, "", "null"):
        metadata_extra["planner_hf_revision"] = str(prev)
    rrev = reviser_cfg.get("revision") or reviser_cfg.get("hf_revision")
    if rrev not in (None, "", "null"):
        metadata_extra["reviser_hf_revision"] = str(rrev)

    for persona, original_plan in tqdm(originals, desc="Condition C (reviser)"):
        reviser_prompt = build_prompt("C", persona, prompts_cfg, small_model_output=original_plan)
        revised_plan = strong_generator.generate(reviser_prompt, default_gen)
        records.append(
            build_output_record(
                persona=persona,
                condition="C",
                model_name=reviser_cfg["display_name"],
                model_path_or_name=str(reviser_cfg["path_or_name"]),
                solution_raw_text=revised_plan,
                metadata=meta_base,
                original_plan=original_plan,
                revised_plan=revised_plan,
                metadata_extra=metadata_extra,
            )
        )
    return records


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Generate training plans for conditions A–D.")
    parser.add_argument("--condition", choices=["A", "B", "C", "D"], required=True)
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

    if args.condition == "C":
        records = run_condition_c(
            personas, models_data, prompts_cfg, generation_cfg, default_gen, generated_at
        )
    else:
        records = run_condition_abd(
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
