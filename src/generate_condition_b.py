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
    parser.add_argument("--output-dir", default="outputs/condition_b")
    args = parser.parse_args()

    personas = load_jsonl(args.input)
    model_cfg = load_yaml(args.models_config)["models"]["small"]
    prompts_cfg = load_yaml(args.prompts_config)
    generation_cfg = load_yaml(args.generation_config)
    default_gen = generation_cfg["default"]
    set_seed(int(default_gen["seed"]))

    generator = build_generator(model_cfg)
    metadata = GenerationMetadata(**default_gen)
    records: List[Dict[str, Any]] = []

    for persona in tqdm(personas, desc="Condition B"):
        prompt = build_prompt("B", persona, prompts_cfg)
        output_text = generator.generate(prompt, default_gen)
        records.append(
            build_output_record(
                persona=persona,
                condition="B",
                model_name=model_cfg["display_name"],
                solution_raw_text=output_text,
                metadata=metadata,
            )
        )

    save_condition_outputs(args.output_dir, records)
    print(f"Saved {len(records)} records to {args.output_dir}")


if __name__ == "__main__":
    main()
