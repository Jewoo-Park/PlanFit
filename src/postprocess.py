from typing import Any, Dict, Optional

from schema import GenerationMetadata, OutputRecord, build_user_payload, merge_metadata


def build_output_record(
    persona: Dict[str, Any],
    condition: str,
    model_name: str,
    model_path_or_name: str,
    solution_raw_text: str,
    metadata: GenerationMetadata,
    original_plan: Optional[str] = None,
    revised_plan: Optional[str] = None,
    metadata_extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    persona_id = str(persona.get("id", "")).strip()
    record = OutputRecord(
        persona_id=persona_id,
        user=build_user_payload(persona),
        condition=condition,
        model_name=model_name,
        model_path_or_name=model_path_or_name,
        solution_raw_text=solution_raw_text,
        metadata=merge_metadata(metadata, metadata_extra),
        original_plan=original_plan,
        revised_plan=revised_plan,
    ).to_dict()
    record["_meta"] = {
        "persona_id": persona_id,
        "persona_name": persona.get("name", ""),
    }
    return record
