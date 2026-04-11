import gc
import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from schema import build_user_payload


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


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def library_versions() -> Dict[str, str]:
    versions: Dict[str, str] = {}
    try:
        import torch

        versions["torch"] = torch.__version__
    except Exception:
        versions["torch"] = "unknown"
    try:
        import transformers

        versions["transformers"] = transformers.__version__
    except Exception:
        versions["transformers"] = "unknown"
    return versions


def set_seed(seed: int, deterministic_cuda: bool = False) -> None:
    random.seed(seed)
    try:
        import os as _os

        _os.environ["PYTHONHASHSEED"] = str(seed)
    except Exception:
        pass
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        if deterministic_cuda:
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
    except Exception:
        pass


def persona_prompt_view(persona: Dict[str, Any]) -> str:
    return json.dumps(build_user_payload(persona), indent=2, ensure_ascii=False)


def save_run_info(
    output_dir: str,
    *,
    condition: str,
    generation_config_path: str,
    models_config_path: str,
    prompts_config_path: str,
    default_gen: Dict[str, Any],
    note: str = "",
) -> None:
    root = ensure_dir(output_dir)
    payload = {
        "condition": condition,
        "generated_at": utc_now_iso(),
        "configs": {
            "generation": generation_config_path,
            "models": models_config_path,
            "prompts": prompts_config_path,
        },
        "default_generation": default_gen,
        "libraries": library_versions(),
        "reproducibility_note": note
        or "temperature>0 uses sampling; exact outputs may vary across runs and hardware.",
    }
    write_json(root / "run_info.json", payload)


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

    def unload(self) -> None:
        if self._model is not None:
            del self._model
            self._model = None
        if self._tokenizer is not None:
            del self._tokenizer
            self._tokenizer = None
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

    def _revision_kw(self) -> Dict[str, Any]:
        rev = self.model_cfg.get("revision") or self.model_cfg.get("hf_revision")
        if rev in (None, "", "null"):
            return {}
        return {"revision": str(rev)}

    def _load(self) -> None:
        if self._tokenizer is not None and self._model is not None:
            return

        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        path_or_name = str(self.model_cfg["path_or_name"]).strip()
        if not path_or_name or path_or_name.startswith("/path/to/"):
            raise ValueError(
                "Invalid model path_or_name in configs/models.yaml. "
                "Set it to a real Hugging Face repo id such as "
                "'Qwen/Qwen3-8B' or 'Qwen/Qwen3-32B-FP8', or to a valid local path."
            )

        hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")
        tokenizer_use_fast = bool(self.model_cfg.get("tokenizer_use_fast", False))
        dtype_str = str(self.model_cfg.get("torch_dtype", "auto"))
        dtype = {
            "float16": torch.float16,
            "bfloat16": torch.bfloat16,
            "float32": torch.float32,
            "auto": "auto",
        }.get(dtype_str, "auto")
        rev_kw = self._revision_kw()

        self._tokenizer = AutoTokenizer.from_pretrained(
            path_or_name,
            token=hf_token,
            use_fast=tokenizer_use_fast,
            trust_remote_code=bool(self.model_cfg.get("trust_remote_code", True)),
            **rev_kw,
        )
        self._model = AutoModelForCausalLM.from_pretrained(
            path_or_name,
            token=hf_token,
            trust_remote_code=bool(self.model_cfg.get("trust_remote_code", True)),
            device_map=self.model_cfg.get("device_map", "auto"),
            torch_dtype=dtype,
            **rev_kw,
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
        param = next(self._model.parameters(), None)
        if param is not None:
            device = param.device
            inputs = {key: value.to(device) for key, value in inputs.items()}

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
