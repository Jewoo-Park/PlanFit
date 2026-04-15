from typing import Any, Dict

from utils import persona_prompt_view, read_text


def load_prompt_template(prompt_key: str, prompts_cfg: Dict[str, Any]) -> str:
    prompt_path = prompts_cfg["prompt_files"][prompt_key]
    return read_text(prompt_path)


def build_prompt_from_key(
    prompt_key: str,
    prompts_cfg: Dict[str, Any],
    **template_vars: Any,
) -> str:
    template = load_prompt_template(prompt_key, prompts_cfg)
    payload: Dict[str, Any] = {}
    for key, value in template_vars.items():
        if key == "persona" and isinstance(value, dict):
            payload[key] = persona_prompt_view(value)
        else:
            payload[key] = value or ""
    return template.format(**payload)


def build_prompt(
    condition: str,
    persona: Dict[str, Any],
    prompts_cfg: Dict[str, Any],
) -> str:
    return build_prompt_from_key(
        condition,
        prompts_cfg,
        persona=persona,
    )
