from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


USER_FIELDS = [
    "age",
    "training_background",
    "primary_goal",
    "secondary_goal",
    "schedule_constraint",
    "injury_or_limitation",
    "preferences",
    "dislikes",
]


@dataclass
class GenerationMetadata:
    prompt_version: str
    temperature: float
    top_p: float
    max_tokens: int
    seed: int


@dataclass
class OutputRecord:
    user: Dict[str, Any]
    condition: str
    model_name: str
    solution_raw_text: str
    metadata: Dict[str, Any]
    original_plan: Optional[str] = None
    revised_plan: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "user": self.user,
            "condition": self.condition,
            "model_name": self.model_name,
            "solution_raw_text": self.solution_raw_text,
            "metadata": self.metadata,
        }
        if self.original_plan is not None:
            payload["original_plan"] = self.original_plan
        if self.revised_plan is not None:
            payload["revised_plan"] = self.revised_plan
        return payload


def build_user_payload(persona: Dict[str, Any]) -> Dict[str, Any]:
    return {field: str(persona.get(field, "")).strip() for field in USER_FIELDS}


def metadata_to_dict(metadata: GenerationMetadata) -> Dict[str, Any]:
    return asdict(metadata)
