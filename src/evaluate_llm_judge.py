import argparse
import json
from typing import Any, Dict, List

from tqdm import tqdm

from utils import build_generator, load_jsonl, load_yaml, read_text, resolve_path, write_jsonl


JUDGE_PROMPT = """You are an evaluation judge for personalized training plans.

Score the candidate plan from 1 to 5 on:
- goal_alignment
- constraint_adherence
- safety
- tradeoff_handling
- progression_coherence

Return strict JSON with this schema:
{
  "goal_alignment": 1-5,
  "constraint_adherence": 1-5,
  "safety": 1-5,
  "tradeoff_handling": 1-5,
  "progression_coherence": 1-5,
  "overall": 1-5,
  "rationale": "short explanation"
}

[User Profile]
{persona}

[Candidate Plan]
{plan}
"""


def parse_json_or_fallback(text: str) -> Dict[str, Any]:
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return {
        "goal_alignment": None,
        "constraint_adherence": None,
        "safety": None,
        "tradeoff_handling": None,
        "progression_coherence": None,
        "overall": None,
        "rationale": text[:500],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outputs", required=True)
    parser.add_argument("--personas", default="data/processed/personas_normalized.jsonl")
    parser.add_argument("--models-config", default="configs/models.yaml")
    parser.add_argument("--evaluation-config", default="configs/evaluation.yaml")
    parser.add_argument("--output-path", default=None)
    args = parser.parse_args()

    records = load_jsonl(args.outputs)
    personas = load_jsonl(args.personas)
    persona_index = {(row.get("age"), row.get("primary_goal"), row.get("secondary_goal")): row for row in personas}

    models_cfg = load_yaml(args.models_config)
    eval_cfg = load_yaml(args.evaluation_config)
    judge_alias = models_cfg.get("judge_model_alias", "strong")
    judge_model_cfg = models_cfg["models"][judge_alias]
    judge_generator = build_generator(judge_model_cfg)
    gen_cfg = eval_cfg["llm_judge"]

    results: List[Dict[str, Any]] = []
    for record in tqdm(records, desc="LLM Judge"):
        key = (
            record["user"]["age"],
            record["user"]["primary_goal"],
            record["user"]["secondary_goal"],
        )
        persona = persona_index.get(key)
        if persona is None:
            continue
        judge_prompt = JUDGE_PROMPT.format(
            persona=json.dumps(persona, ensure_ascii=False, indent=2),
            plan=record["solution_raw_text"],
        )
        raw_judgment = judge_generator.generate(judge_prompt, gen_cfg)
        results.append(
            {
                "condition": record["condition"],
                "model_name": record["model_name"],
                "persona_id": persona.get("id", ""),
                "judgment": parse_json_or_fallback(raw_judgment),
                "raw_judgment_text": raw_judgment,
            }
        )

    output_path = args.output_path or str(resolve_path(args.outputs).with_name("evaluation_llm_judge.jsonl"))
    write_jsonl(output_path, results)
    print(f"Wrote {len(results)} LLM-judge evaluations to {output_path}")


if __name__ == "__main__":
    main()
