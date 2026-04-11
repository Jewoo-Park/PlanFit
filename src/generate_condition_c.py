import argparse
from typing import Any, Dict, List

from tqdm import tqdm

from postprocess import build_output_record
from prompt_builder import build_prompt
from schema import GenerationMetadata
from utils import build_generator, load_jsonl, load_yaml, save_condition_outputs, set_seed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed/personas_normalized.jsonl")
    parser.add_argument("--models-config", default="configs/models.yaml")
    parser.add_argument("--prompts-config", default="configs/prompts.yaml")
    parser.add_argument("--generation-config", default="configs/generation.yaml")
    parser.add_argument("--output-dir", default="outputs/condition_c")
    args = parser.parse_args()

    personas = load_jsonl(args.input)
    models_cfg = load_yaml(args.models_config)["models"]
    prompts_cfg = load_yaml(args.prompts_config)
    generation_cfg = load_yaml(args.generation_config)
    default_gen = generation_cfg["default"]
    set_seed(int(default_gen["seed"]))

    small_generator = build_generator(models_cfg["small"])
    strong_generator = build_generator(models_cfg["strong"])
    metadata = GenerationMetadata(**default_gen)
    records: List[Dict[str, Any]] = []

    for persona in tqdm(personas, desc="Condition C"):
        original_prompt = build_prompt("A", persona, prompts_cfg)
        original_plan = small_generator.generate(original_prompt, default_gen)

        reviser_prompt = build_prompt("C", persona, prompts_cfg, small_model_output=original_plan)
        revised_plan = strong_generator.generate(reviser_prompt, default_gen)

        records.append(
            build_output_record(
                persona=persona,
                condition="C",
                model_name=models_cfg["strong"]["display_name"],
                solution_raw_text=revised_plan,
                metadata=metadata,
                original_plan=original_plan,
                revised_plan=revised_plan,
            )
        )

    save_condition_outputs(args.output_dir, records)
    print(f"Saved {len(records)} records to {args.output_dir}")


if __name__ == "__main__":
    main()
