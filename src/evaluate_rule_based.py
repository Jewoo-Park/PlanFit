import argparse
import re
from typing import Any, Dict, List

from utils import load_jsonl, load_yaml, resolve_path, write_jsonl


def parse_schedule_limit(schedule_text: str) -> Dict[str, int]:
    days_match = re.search(r"(\d+)\s*(?:to|–|-)?\s*(\d+)?\s*days per week", schedule_text.lower())
    mins_match = re.search(r"(\d+)\s*(?:to|–|-)?\s*(\d+)?\s*minutes per session", schedule_text.lower())
    return {
        "max_days": int(days_match.group(2) or days_match.group(1)) if days_match else 7,
        "max_minutes": int(mins_match.group(2) or mins_match.group(1)) if mins_match else 999,
    }


def duration_check(output_text: str, max_minutes: int) -> float:
    durations = [int(x) for x in re.findall(r"Estimated duration \(minutes\):\s*(\d+)", output_text)]
    if not durations:
        return 0.0
    return 1.0 if max(durations) <= max_minutes else 0.0


def day_count_check(output_text: str, max_days: int) -> float:
    weeks = re.split(r"\nWeek\s+\d+\n", "\n" + output_text)
    counts = []
    for chunk in weeks:
        if "- Day:" not in chunk:
            continue
        day_blocks = chunk.split("- Week:")
        training_days = 0
        for block in day_blocks:
            if not block.strip():
                continue
            focus_match = re.search(r"- Main focus:\s*(.+)", block)
            focus_text = focus_match.group(1).strip().lower() if focus_match else ""
            if "rest" not in focus_text and "recovery" not in focus_text:
                training_days += 1
        counts.append(training_days)
    if not counts:
        return 0.0
    return 1.0 if max(counts) <= max_days else 0.0


def keyword_score(text: str, keywords: List[str]) -> float:
    lower = text.lower()
    hits = sum(1 for kw in keywords if kw.lower() in lower)
    return min(1.0, hits / max(1, min(3, len(keywords))))


def limitation_score(persona: Dict[str, Any], output_text: str, eval_cfg: Dict[str, Any]) -> float:
    limitation = persona.get("injury_or_limitation", "").lower()
    keyword_map = eval_cfg["rule_based"]["limitation_keywords"]
    if "no major injury" in limitation or "no injury" in limitation:
        return 1.0
    if "back" in limitation:
        return keyword_score(output_text, keyword_map["lower-back"])
    if "knee" in limitation:
        return keyword_score(output_text, keyword_map["knee"])
    if "upper limb" in limitation or "grip strength" in limitation or "shoulder range" in limitation:
        return keyword_score(output_text, keyword_map["upper-limb"])
    if "calf" in limitation:
        return keyword_score(output_text, keyword_map["calf"])
    return 0.5


def evaluate_record(record: Dict[str, Any], persona: Dict[str, Any], eval_cfg: Dict[str, Any]) -> Dict[str, Any]:
    text = record["solution_raw_text"]
    limits = parse_schedule_limit(persona.get("schedule_constraint", ""))
    weights = eval_cfg["rule_based"]["weights"]

    goal_keywords = [persona.get("primary_goal", ""), "priority", "trade-off"]
    progression_keywords = ["week 1", "week 2", "week 3", "week 4", "progression"]

    scores = {
        "goal_alignment": keyword_score(text, goal_keywords),
        "schedule_compliance": 0.5 * duration_check(text, limits["max_minutes"]) + 0.5 * day_count_check(text, limits["max_days"]),
        "limitation_handling": limitation_score(persona, text, eval_cfg),
        "tradeoff_handling": keyword_score(text, ["trade-off", persona.get("primary_goal", ""), persona.get("secondary_goal", "")]),
        "progression_coherence": keyword_score(text, progression_keywords),
    }

    overall = sum(scores[key] * weights[key] for key in weights)
    return {
        "persona_id": persona.get("id", ""),
        "condition": record["condition"],
        "model_name": record["model_name"],
        "scores": scores,
        "weighted_score": round(overall, 4),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outputs", required=True)
    parser.add_argument("--personas", default="data/processed/personas_normalized.jsonl")
    parser.add_argument("--evaluation-config", default="configs/evaluation.yaml")
    parser.add_argument("--output-path", default=None)
    args = parser.parse_args()

    records = load_jsonl(args.outputs)
    personas = {row["id"]: row for row in load_jsonl(args.personas)}
    eval_cfg = load_yaml(args.evaluation_config)

    results = []
    for record in records:
        persona = next(
            (row for row in personas.values() if row.get("age") == record["user"]["age"] and row.get("primary_goal") == record["user"]["primary_goal"]),
            None,
        )
        if persona is None:
            continue
        results.append(evaluate_record(record, persona, eval_cfg))

    output_path = args.output_path or str(resolve_path(args.outputs).with_name("evaluation_rule_based.jsonl"))
    write_jsonl(output_path, results)
    print(f"Wrote {len(results)} rule-based evaluations to {output_path}")


if __name__ == "__main__":
    main()
