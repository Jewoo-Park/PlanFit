# training-planner-llm

현실적인 4주 운동 계획 생성 능력을 평가하기 위한 실험 레포입니다. 이 레포는 사용자 페르소나 JSONL을 입력으로 받아 `Qwen 3 8B`와 `Qwen 3 32B`를 사용해 조건 `A/B/C/D` 실험을 실행하고, 결과를 저장하고, 규칙 기반 또는 LLM judge 기반 평가를 수행할 수 있도록 구성되어 있습니다.

## 실험 목적

1. LLM이 목표, 일정 제약, 선호, 부상/제한사항을 반영한 고수준 planning을 수행할 수 있는지 평가
2. 근비대 vs 러닝 유지, 감량 vs 근유지 같은 trade-off를 인지하고 합리적으로 절충하는지 평가

## 레포 구조

```text
training-planner-llm/
├─ README.md
├─ requirements.txt
├─ .gitignore
├─ configs/
├─ data/
├─ prompts/
├─ src/
├─ scripts/
├─ outputs/
└─ logs/
```

## 빠른 시작

1. 의존성 설치

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Colab에서는 아래를 먼저 권장합니다.

```bash
pip install -U pip
pip install -r requirements.txt
```

2. `configs/models.yaml`에서 실제 모델 경로 또는 Hugging Face ID를 수정

3. 페르소나 정규화

```bash
python3 src/load_personas.py
```

4. 조건별 생성 실행

```bash
bash scripts/run_condition_a.sh
bash scripts/run_condition_b.sh
bash scripts/run_condition_c.sh
bash scripts/run_condition_d.sh
```

또는 전체 실행:

```bash
bash scripts/run_all.sh
```

## Colab 실행 팁

Hugging Face 다운로드가 느리거나 멈추는 경우가 있으므로, Colab에서는 아래 순서를 권장합니다.

```python
from huggingface_hub import login
login()
```

```bash
export HF_HUB_ENABLE_HF_TRANSFER=1
python src/load_personas.py
python src/generate_condition_a.py
```

기본 `configs/models.yaml`은 아래 두 모델을 사용하도록 설정되어 있습니다.

- `Qwen/Qwen3-8B`
- `Qwen/Qwen3-32B-FP8`

기본값으로 `tokenizer_use_fast: false`를 사용하므로, `tokenizer.json` 다운로드가 불안정한 환경에서도 상대적으로 안정적으로 시작할 수 있습니다.

## 입력 데이터 형식

기본 입력 파일은 `data/raw/personas.jsonl`입니다. 한 줄당 한 개의 JSON 객체를 사용합니다. 이 레포는 학습이 아니라 추론 실험용이므로 `train/dev/test` split을 기본 구조에 두지 않습니다. 최소 필드는 아래와 같습니다.

```json
{
  "id": "P1",
  "name": "Junsu",
  "age": "25",
  "training_background": "...",
  "primary_goal": "...",
  "secondary_goal": "...",
  "schedule_constraint": "...",
  "injury_or_limitation": "...",
  "preferences": "...",
  "dislikes": "..."
}
```

추가로 평가용 메모(`must_reflect_constraints`, `dangerous_plan_examples`, `major_deduction_points`)를 포함할 수 있습니다.

## 출력 형식

조건 `A/B/D`는 각 샘플을 아래 형식으로 저장합니다.

```json
{
  "user": {
    "age": "",
    "training_background": "",
    "primary_goal": "",
    "secondary_goal": "",
    "schedule_constraint": "",
    "injury_or_limitation": "",
    "preferences": "",
    "dislikes": ""
  },
  "condition": "A | B | D",
  "model_name": "string",
  "solution_raw_text": "full model output",
  "metadata": {
    "prompt_version": "v1",
    "temperature": 0.7,
    "top_p": 0.9,
    "max_tokens": 2048,
    "seed": 42
  }
}
```

조건 `C`는 아래 필드를 추가로 저장합니다.

```json
{
  "original_plan": "string",
  "revised_plan": "string"
}
```

## 실행 흐름

- `A`: 소형 모델 direct planner
- `B`: 소형 모델 structured planner
- `C`: 소형 모델로 `A` 생성 후, 대형 모델 reviser로 수정
- `D`: 대형 모델 direct planner

## 평가

### 규칙 기반 평가

```bash
python3 src/evaluate_rule_based.py \
  --outputs outputs/condition_a/results.jsonl \
  --personas data/processed/personas_normalized.jsonl
```

### LLM judge 평가

```bash
python3 src/evaluate_llm_judge.py \
  --outputs outputs/condition_a/results.jsonl \
  --personas data/processed/personas_normalized.jsonl
```

## 주의

- `Qwen 3 32B`는 큰 메모리를 요구할 수 있으므로 실제 사용 환경에 맞는 양자화 모델 또는 로컬 경로를 `configs/models.yaml`에서 설정해야 합니다.
- 이 레포는 의료 조언을 하지 않으며, 프롬프트 차원의 안전 제약만 평가합니다.
