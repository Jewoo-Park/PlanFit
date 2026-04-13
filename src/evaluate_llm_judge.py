import argparse
import json
from typing import Any, Dict, List, Optional

from tqdm import tqdm

from utils import build_generator, load_jsonl, load_yaml, read_text, resolve_path, write_jsonl

DEFAULT_METRICS = [
    "goal_alignment",
    "constraint_adherence",
    "safety",
    "tradeoff_handling",
    "progression_coherence",
]


def _coerce_score(value: Any, scale_min: int, scale_max: int) -> Optional[int]:
    if isinstance(value, bool) or value is None:
        return None
    numeric: Optional[float] = None
    if isinstance(value, (int, float)):
        numeric = float(value)
    elif isinstance(value, str):
        try:
            numeric = float(value.strip())
        except ValueError:
            return None
    if numeric is None:
        return None
    clamped = max(scale_min, min(scale_max, int(round(numeric))))
    return clamped


def _normalize_judgment(
    payload: Dict[str, Any],
    metrics: List[str],
    scale_min: int,
    scale_max: int,
    fallback_rationale: str = "",
) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    for metric in metrics + ["overall"]:
        normalized[metric] = _coerce_score(payload.get(metric), scale_min, scale_max)

    major_issues = payload.get("major_issues", [])
    if isinstance(major_issues, list):
        normalized["major_issues"] = [str(item).strip() for item in major_issues if str(item).strip()][:4]
    elif major_issues in (None, ""):
        normalized["major_issues"] = []
    else:
        normalized["major_issues"] = [str(major_issues).strip()]

    rationale = str(payload.get("rationale") or fallback_rationale).strip()
    normalized["rationale"] = rationale[:1000]
    return normalized


def _json_schema(metrics: List[str], scale_min: int, scale_max: int) -> str:
    lines = ["{"]
    for metric in metrics:
        lines.append(f'  "{metric}": {scale_min}-{scale_max},')
    lines.extend(
        [
            f'  "overall": {scale_min}-{scale_max},',
            '  "major_issues": ["short issue 1", "short issue 2"],',
            '  "rationale": "short critical explanation"',
            "}",
        ]
    )
    return "\n".join(lines)


def _metrics_block(metrics: List[str]) -> str:
    return "\n".join(f"- {metric}" for metric in metrics)


def build_judge_prompt(
    prompt_template: str,
    *,
    persona: Dict[str, Any],
    plan: str,
    metrics: List[str],
    scale_min: int,
    scale_max: int,
) -> str:
    return prompt_template.format(
        scale_min=scale_min,
        scale_max=scale_max,
        metrics_block=_metrics_block(metrics),
        json_schema=_json_schema(metrics, scale_min, scale_max),
        persona=json.dumps(persona, ensure_ascii=False, indent=2),
        plan=plan,
    )


def parse_json_or_fallback(
    text: str,
    *,
    metrics: List[str],
    scale_min: int,
    scale_max: int,
) -> Dict[str, Any]:
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            payload = json.loads(text[start : end + 1])
            if isinstance(payload, dict):
                return _normalize_judgment(payload, metrics, scale_min, scale_max, fallback_rationale=text[:500])
        except json.JSONDecodeError:
            pass
    return _normalize_judgment({}, metrics, scale_min, scale_max, fallback_rationale=text[:500])


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
    metrics = list(gen_cfg.get("metrics", DEFAULT_METRICS))
    scale_min = int(gen_cfg.get("scale_min", 1))
    scale_max = int(gen_cfg.get("scale_max", 10))
    prompt_template = read_text(str(gen_cfg.get("prompt_path", "prompts/judge_rubric.txt")))

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
        judge_prompt = build_judge_prompt(
            prompt_template,
            persona=persona,
            plan=record["solution_raw_text"],
            metrics=metrics,
            scale_min=scale_min,
            scale_max=scale_max,
        )
        raw_judgment = judge_generator.generate(judge_prompt, gen_cfg)
        results.append(
            {
                "condition": record["condition"],
                "model_name": record["model_name"],
                "persona_id": persona.get("id", ""),
                "judgment": parse_json_or_fallback(
                    raw_judgment,
                    metrics=metrics,
                    scale_min=scale_min,
                    scale_max=scale_max,
                ),
                "raw_judgment_text": raw_judgment,
            }
        )

    output_path = args.output_path or str(resolve_path(args.outputs).with_name("evaluation_llm_judge.jsonl"))
    write_jsonl(output_path, results)
    print(f"Wrote {len(results)} LLM-judge evaluations to {output_path}")


if __name__ == "__main__":
    main()
