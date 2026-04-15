# PlanFit

`PlanFit`은 4주 personalized hybrid training plan generation을 대상으로, **multi-objective planning task에서 소형 LLM의 한계를 드러내고**, structured prompting과 workflow 설계가 그 한계를 어디까지 보완할 수 있는지 평가하는 실험 레포입니다.

이번 과제의 핵심은 "workflow를 쓰면 다 좋아진다"를 보이는 것이 아니라, **멀티오브젝티브 계획 생성은 소형 모델에서 특히 취약하며, 개선 효과 또한 모델 capacity에 따라 다르게 나타난다**는 점을 검증하는 것입니다.

## 현재 문서의 기준

이 README는 **과제 보고서용 condition label**을 기준으로 실험을 설명합니다.  
README에서는 `A/B/C/D/E/F`를 아래 순서로 사용합니다.

- `A`: `Qwen3-0.6B` direct
- `B`: `Qwen3-1.7B` direct
- `C`: `Qwen3-1.7B` structured
- `D`: `Qwen3-14B-AWQ` direct
- `E`: `Qwen3-1.7B` workflow
- `F`: `Qwen3-0.6B` workflow

다만 현재 코드 실행 이름은 아직 legacy mapping을 유지하며, 실제 workflow runner는 code condition `C/F`에 연결되어 있습니다.

## Research Questions

1. personalized hybrid training plan generation 같은 multi-objective task에서 `Qwen3-0.6B`, `Qwen3-1.7B`, `Qwen3-14B-AWQ`는 어떤 failure gap을 보이는가?
2. `Qwen3-1.7B direct`에 structured prompting을 더하면, small-model failure를 어느 정도 완화할 수 있는가?
3. 동일한 workflow decomposition이 `Qwen3-1.7B`와 `Qwen3-0.6B`에 모두 도움이 되는가, 아니면 capacity limit 때문에 효과가 갈리는가?

## 고정할 실험 범위

- Task: 4주 personalized hybrid training plan generation
- Core rubric: `Constraint`, `Safety`, `Goal alignment`, `Trade-off`, `Coherence`
- Output schema: `Week / Day / Focus / Session / Duration / Intensity / Reason`
- Evaluation protocol: blind human scoring + quantitative/qualitative analysis 분리

즉, rubric은 유지하고 model/system condition만 바꾸는 방향으로 갑니다.

## 메인 실험 조건

이번 과제에서는 workflow 조건을 `E/F`로 두고, `A-D`를 baseline block으로 해석합니다.

| Condition | Model | System | Purpose |
| --- | --- | --- | --- |
| `A` | `Qwen3-0.6B` | Direct planner | 극소형 모델 direct baseline |
| `B` | `Qwen3-1.7B` | Direct planner | 소형 모델 direct baseline |
| `C` | `Qwen3-1.7B` | Structured planner | prompt structuring baseline |
| `D` | `Qwen3-14B-AWQ` | Direct planner | local stronger reference |
| `E` | `Qwen3-1.7B` | LangGraph workflow planner | workflow intervention on small model |
| `F` | `Qwen3-0.6B` | LangGraph workflow planner | 동일 workflow의 tiny-model 한계 확인 |

`0.6B structured`는 현재 메인 비교축에서 제외하고, 이 README는 `A -> B -> C -> D`의 baseline 흐름 뒤에 `E/F` workflow 조건을 붙여 읽는 구성으로 정리합니다.

## Workflow 정의

`E/F`의 핵심은 **같은 모델을 유지한 채 시스템 설계만 바꾸었을 때 어떤 모델에서는 개선이 가능하고 어떤 모델에서는 한계가 더 분명해지는지**를 보는 것입니다.

권장 workflow는 아래 순서를 따릅니다.

1. `profile extractor`
2. `goal prioritizer`
3. `draft planner`
4. `safety checker`
5. `constraint checker`
6. `trade-off checker`
7. `final integrator / formatter`

이 구조를 통해 다음 비교를 명확하게 만듭니다.

- `A` vs `B`: `0.6B`와 `1.7B` direct 사이의 capacity gap은 얼마나 큰가
- `C` vs `B`: structured prompt만으로도 `1.7B` failure를 줄일 수 있는가
- `D` vs `A/B/C`: stronger reference 대비 small-model weakness는 어디서 나타나는가
- `E` vs `B/C/D`: `1.7B + workflow`가 small-model 한계를 얼마나 회복할 수 있는가
- `F` vs `A`: 같은 workflow가 `0.6B`에는 도움이 되는가, 아니면 한계를 더 드러내는가

## 허점 분석 프레임

현재 분석은 아래 축을 기준으로 진행합니다.

| 현재 분석 축 | 설명 |
| --- | --- |
| small model 대표 실패 유형 | `A/B/C/D`에서 나타나는 multi-objective planning failure 분포 |
| workflow가 줄인 오류 | `E/F workflow`가 줄인 오류 |
| workflow 이후에도 남는 오류 | workflow 이후에도 남거나 더 악화되는 오류 |
| strong direct 안정성 | `D` (`14B-AWQ direct`)가 local reference로 얼마나 안정적인가 |
| workflow trace 반영 여부 | `E/F`의 intermediate state가 제약을 제대로 반영하는가 |

권장 failure tagging은 아래와 같습니다.

| Failure type | Status label | Workflow-specific field |
| --- | --- | --- |
| Constraint violation | `fixed / partly fixed / not fixed` | `caught_by_node` |
| Safety issue | `fixed / partly fixed / not fixed` | `caught_by_node` |
| Goal misunderstanding | `fixed / not fixed` | `caught_by_node` |
| Trade-off failure | `fixed / partly fixed / not fixed` | `caught_by_node` |
| Long-term coherence issue | `fixed / not fixed` | `caught_by_node` |

`caught_by_node`는 `extractor / safety checker / constraint checker / trade-off checker / not caught`처럼 기록합니다.

## 추가 연구용 메타데이터

현재 `results.jsonl`의 `metadata`에는 아래 필드가 저장됩니다.

공통 저장 필드:

- `prompt_version`
- `temperature`
- `top_p`
- `max_tokens`
- `seed`
- `generated_at`
- `prompt_files`
- `system_type`

Workflow 조건(`E`, `F`)에서 추가 저장되는 필드:

- `model_calls`
- `checker_fail_count`
- `revision_loops`
- `caught_by_node`
- `remaining_fail_nodes`
- `workflow_nodes`
- `workflow_trace`
- `profile_summary`
- `goal_strategy`
- `safety_review`
- `constraint_review`
- `tradeoff_review`



### Experiment

- Full result block: `10 personas x A/B/C/D/E/F = 60 outputs`

보고서 본문도 `A/B/C/D/E/F` 전체 비교를 기준으로 구성하되, `A-D`에서 baseline weakness를 먼저 보여주고 `E/F`에서 workflow effect의 model-dependence를 해석하는 방향으로 잡습니다.

## 현재 코드베이스와의 매핑

현재 레포의 실행 라벨은 아직 legacy 상태라서, README label과 code condition은 아래처럼 대응합니다.

| README label | Experiment meaning | Current code condition |
| --- | --- | --- |
| `A` | `0.6B` direct planner | `E` |
| `B` | `1.7B` direct planner | `A` |
| `C` | `1.7B` structured planner | `B` |
| `D` | `14B-AWQ` direct planner | `D` |
| `E` | `1.7B` LangGraph workflow planner | `C` |
| `F` | `0.6B` LangGraph workflow planner | `F` |

현재 `configs/models.yaml` 기본값은 아래처럼 되어 있습니다.

- `tiny = Qwen/Qwen3-0.6B`
- `small = Qwen/Qwen3-1.7B`
- `strong = Qwen/Qwen3-14B-AWQ`

즉 현재 코드도 이미 on-device 실험 설계에 맞춘 상태입니다.

## Working Environment

앞으로 로컬 작업은 모두 `conda` 환경 `nlp`를 기준으로 진행합니다.

```bash
conda activate nlp
```

의존성 설치도 같은 환경에서 수행합니다.

```bash
conda activate nlp
pip install -r requirements.txt
```

## 현재 기준 실행 명령

코드 리팩터링 전까지는 기존 엔트리포인트를 그대로 사용합니다.  
아래 스크립트 이름은 **README label이 아니라 current code condition 기준**입니다.

```bash
conda activate nlp
python src/load_personas.py
bash scripts/run_condition_a.sh
bash scripts/run_condition_b.sh
bash scripts/run_condition_c.sh
bash scripts/run_condition_d.sh
bash scripts/run_condition_e.sh
bash scripts/run_condition_f.sh
```

전체 실행:

```bash
conda activate nlp
bash scripts/run_all.sh
```

## 현재 기준 평가 명령

규칙 기반 평가:

```bash
conda activate nlp
python src/evaluate_rule_based.py \
  --outputs outputs/condition_a/results.jsonl \
  --personas data/processed/personas_normalized.jsonl
```

LLM judge 평가:

```bash
conda activate nlp
python src/evaluate_llm_judge.py \
  --outputs outputs/condition_a/results.jsonl \
  --personas data/processed/personas_normalized.jsonl
```

현재 LLM judge는 `1-10` 스케일을 사용하며, 비판적 rubric은 [prompts/judge_rubric.txt](/home/gon-mac/local/NLP-Proj/prompts/judge_rubric.txt)에, 관련 설정은 [configs/evaluation.yaml](/home/gon-mac/local/NLP-Proj/configs/evaluation.yaml)에 있습니다.

## 입력 데이터

기본 입력 파일은 `data/raw/personas.jsonl`이며, 한 줄당 한 개의 JSON 객체를 사용합니다. 최소 필드는 아래와 같습니다.

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

추가로 평가용 메모(`must_reflect_constraints`, `dangerous_plan_examples`, `major_deduction_points`)를 함께 둘 수 있습니다.

## 메인 메시지

> multi-objective planning은 소형 LLM에서 특히 취약하며, structured prompting과 workflow의 효과도 모델 capacity에 강하게 의존한다.

**small-model limitation을 드러낸 뒤, 시스템 설계가 그 한계를 어디까지 보완할 수 있고 어디서는 실패하는지 알 수 있다**
