import argparse
from typing import Any, Dict, List

from utils import load_jsonl, resolve_path, write_jsonl


FIELD_ALIASES = {
    "training background": "training_background",
    "primary goal": "primary_goal",
    "secondary goal": "secondary_goal",
    "schedule constraint": "schedule_constraint",
    "injury / physical limitation": "injury_or_limitation",
}


def normalize_keys(row: Dict[str, Any]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    for key, value in row.items():
        clean = key.strip().lower().replace("-", "_")
        clean = FIELD_ALIASES.get(clean, clean)
        normalized[clean] = value
    return normalized


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/raw/personas.jsonl")
    parser.add_argument("--normalized-output", default="data/processed/personas_normalized.jsonl")
    args = parser.parse_args()

    raw_rows = load_jsonl(args.input)
    normalized_rows: List[Dict[str, Any]] = []
    for idx, row in enumerate(raw_rows, start=1):
        item = normalize_keys(row)
        item.setdefault("id", f"P{idx}")
        item.setdefault("name", item["id"])
        normalized_rows.append(item)

    write_jsonl(args.normalized_output, normalized_rows)

    print(f"Loaded {len(raw_rows)} personas")
    print(f"Wrote normalized personas to {resolve_path(args.normalized_output)}")


if __name__ == "__main__":
    main()
