from typing import Any, Dict, Optional

from utils import persona_prompt_view, read_text, resolve_path


def load_prompt_template(condition: str, prompts_cfg: Dict[str, Any]) -> str:
    prompt_path = prompts_cfg["prompt_files"][condition]
    return read_text(prompt_path)


def build_prompt(
    condition: str,
    persona: Dict[str, Any],
    prompts_cfg: Dict[str, Any],
    small_model_output: Optional[str] = None,
) -> str:
    template = load_prompt_template(condition, prompts_cfg)
    payload = {
        "persona": persona_prompt_view(persona),
        "small_model_output": small_model_output or "",
    }
    return template.format(**payload)
