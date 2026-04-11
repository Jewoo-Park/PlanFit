from typing import Any, Dict, Optional

from schema import GenerationMetadata, OutputRecord, build_user_payload, metadata_to_dict


def build_output_record(
    persona: Dict[str, Any],
    condition: str,
    model_name: str,
    solution_raw_text: str,
    metadata: GenerationMetadata,
    original_plan: Optional[str] = None,
    revised_plan: Optional[str] = None,
) -> Dict[str, Any]:
    record = OutputRecord(
        user=build_user_payload(persona),
        condition=condition,
        model_name=model_name,
        solution_raw_text=solution_raw_text,
        metadata=metadata_to_dict(metadata),
        original_plan=original_plan,
        revised_plan=revised_plan,
    ).to_dict()
    record["_meta"] = {
        "persona_id": persona.get("id", ""),
        "persona_name": persona.get("name", ""),
    }
    return record
