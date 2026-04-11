import json
import random
from pathlib import Path
from typing import Any, Dict, List

import yaml


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else project_root() / path


def load_yaml(path_str: str) -> Dict[str, Any]:
    return yaml.safe_load(resolve_path(path_str).read_text(encoding="utf-8"))


def read_text(path_str: str) -> str:
    return resolve_path(path_str).read_text(encoding="utf-8")


def load_jsonl(path_str: str) -> List[Dict[str, Any]]:
    path = resolve_path(path_str)
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def write_jsonl(path_str: str, rows: List[Dict[str, Any]]) -> None:
    path = resolve_path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def ensure_dir(path_str: str) -> Path:
    path = resolve_path(path_str)
    path.mkdir(parents=True, exist_ok=True)
    return path


def set_seed(seed: int) -> None:
    random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except Exception:
        pass


def persona_prompt_view(persona: Dict[str, Any]) -> str:
    filtered = {
        "age": persona.get("age", ""),
        "training_background": persona.get("training_background", ""),
        "primary_goal": persona.get("primary_goal", ""),
        "secondary_goal": persona.get("secondary_goal", ""),
        "schedule_constraint": persona.get("schedule_constraint", ""),
        "injury_or_limitation": persona.get("injury_or_limitation", ""),
        "preferences": persona.get("preferences", ""),
        "dislikes": persona.get("dislikes", ""),
    }
    return json.dumps(filtered, indent=2, ensure_ascii=False)


def save_condition_outputs(output_dir: str, records: List[Dict[str, Any]]) -> None:
    output_root = ensure_dir(output_dir)
    records_dir = output_root / "records"
    records_dir.mkdir(parents=True, exist_ok=True)
    for idx, record in enumerate(records, start=1):
        persona_id = record.get("_meta", {}).get("persona_id", f"sample_{idx:03d}")
        clean_record = {k: v for k, v in record.items() if k != "_meta"}
        write_json(records_dir / f"{persona_id}.json", clean_record)
    write_jsonl(str(output_root / "results.jsonl"), [{k: v for k, v in r.items() if k != "_meta"} for r in records])


class HFTextGenerator:
    def __init__(self, model_cfg: Dict[str, Any]) -> None:
        self.model_cfg = model_cfg
        self.model_name = model_cfg["display_name"]
        self._tokenizer = None
        self._model = None

    def _load(self) -> None:
        if self._tokenizer is not None and self._model is not None:
            return

        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        dtype_str = str(self.model_cfg.get("torch_dtype", "auto"))
        dtype = {
            "float16": torch.float16,
            "bfloat16": torch.bfloat16,
            "float32": torch.float32,
            "auto": "auto",
        }.get(dtype_str, "auto")

        self._tokenizer = AutoTokenizer.from_pretrained(
            self.model_cfg["path_or_name"],
            trust_remote_code=bool(self.model_cfg.get("trust_remote_code", True)),
        )
        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_cfg["path_or_name"],
            trust_remote_code=bool(self.model_cfg.get("trust_remote_code", True)),
            device_map=self.model_cfg.get("device_map", "auto"),
            torch_dtype=dtype,
        )
        if self._tokenizer.pad_token_id is None and self._tokenizer.eos_token_id is not None:
            self._tokenizer.pad_token_id = self._tokenizer.eos_token_id

    def generate(self, prompt: str, gen_cfg: Dict[str, Any]) -> str:
        self._load()

        do_sample = float(gen_cfg["temperature"]) > 0.0
        use_chat_template = bool(self.model_cfg.get("use_chat_template", True))
        if use_chat_template and getattr(self._tokenizer, "chat_template", None):
            prompt_text = self._tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}],
                tokenize=False,
                add_generation_prompt=True,
            )
        else:
            prompt_text = prompt

        inputs = self._tokenizer(prompt_text, return_tensors="pt")
        try:
            model_device = self._model.device
            inputs = {key: value.to(model_device) for key, value in inputs.items()}
        except Exception:
            pass

        output_ids = self._model.generate(
            **inputs,
            max_new_tokens=int(gen_cfg["max_tokens"]),
            temperature=float(gen_cfg["temperature"]),
            top_p=float(gen_cfg["top_p"]),
            do_sample=do_sample,
            pad_token_id=self._tokenizer.pad_token_id,
            eos_token_id=self._tokenizer.eos_token_id,
        )
        generated_ids = output_ids[0][inputs["input_ids"].shape[1] :]
        text = self._tokenizer.decode(generated_ids, skip_special_tokens=True)
        return text.strip()


def build_generator(model_cfg: Dict[str, Any]) -> HFTextGenerator:
    backend = model_cfg.get("backend", "transformers")
    if backend != "transformers":
        raise ValueError(f"Unsupported backend: {backend}")
    return HFTextGenerator(model_cfg)
