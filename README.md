# PlanFit

`PlanFit`은 4주 personalized hybrid training plan generation을 대상으로, **multi-objective planning task에서 소형 LLM의 한계를 드러내고**, structured prompting과 workflow 설계가 그 한계를 어디까지 보완할 수 있는지 평가하는 실험 레포입니다.

이번 과제의 핵심은 "workflow를 쓰면 다 좋아진다"를 보이는 것이 아니라, **멀티오브젝티브 계획 생성은 소형 모델에서 특히 취약하며, 개선 효과 또한 모델 capacity에 따라 다르게 나타난다**는 점을 검증하는 것입니다.

## 문서 기준

이 README와 실제 코드 실행 라벨은 같은 condition 순서를 사용합니다.

- `A`: `Qwen3-0.6B` direct
- `B`: `Qwen3-1.7B` direct
- `C`: `Qwen3-1.7B` structured
- `D`: `Qwen3-14B-AWQ` direct
- `E`: `Qwen3-1.7B` workflow
- `F`: `Qwen3-0.6B` workflow
- `G`: `Qwen3-0.6B` structured ablation
- `H`: `Qwen3-14B-AWQ` structured ablation

----- extra work -----
- `I`: `Qwen3-1.7B` refined workflow
- `J`: `Qwen3-0.6B` refined workflow

## Research Questions

1. personalized hybrid training plan generation 같은 multi-objective task에서 planning performance는 **model size**와 **prompting strategy** (`direct` vs. `structured`)에 따라 어떻게 달라지는가?
2. **workflow-based system design**은 planning performance를 개선할 수 있는가? 특히 compact model에서 그 효과가 더 크게 나타나는가?

## 고정할 실험 범위

- Task: 4주 personalized hybrid training plan generation
- Core rubric: `Constraint`, `Safety`, `Goal alignment`, `Trade-off`, `Coherence`
- Output schema: `Week / Day / Focus / Session / Duration / Intensity / Reason`
- Evaluation protocol: blind human scoring + quantitative/qualitative analysis 분리

즉, rubric은 유지하고 model/system condition만 바꾸는 방향으로 갑니다.

## 메인 실험 조건

이번 과제에서는 workflow 조건을 `E/F`로 두고, `A-D`를 main comparison block으로 해석합니다.

| Condition | Model | System | Purpose |
| --- | --- | --- | --- |
| `A` | `Qwen3-0.6B` | Direct planner | 극소형 모델 direct baseline |
| `B` | `Qwen3-1.7B` | Direct planner | 소형 모델 direct baseline |
| `C` | `Qwen3-1.7B` | Structured planner | prompt structuring baseline |
| `D` | `Qwen3-14B-AWQ` | Direct planner | local stronger reference |
| `E` | `Qwen3-1.7B` | LangGraph workflow planner | workflow intervention on small model |
| `F` | `Qwen3-0.6B` | LangGraph workflow planner | 동일 workflow의 tiny-model 한계 확인 |

추가 structured ablation 조건은 아래처럼 별도로 둡니다.

| Condition | Model | System | Purpose |
| --- | --- | --- | --- |
| `G` | `Qwen3-0.6B` | Structured planner | tiny-model structured ablation |
| `H` | `Qwen3-14B-AWQ` | Structured planner | strong-model structured ablation |

즉 메인 읽기 순서는 `A -> B -> C -> D -> E -> F`로 유지하고, `G/H`는 capacity 양 끝단에서 `direct` 대비 `structured` prompting 효과를 확인하는 ablation block으로 해석합니다.

## 과제 외 추가 실험

`I/J`는 과제 본문 비교축과 분리된 추가 실험으로 두고, workflow tuning 과정에서 최종적으로 남긴 refined workflow 설정을 사용합니다.

| Condition | Model | System | Purpose |
| --- | --- | --- | --- |
| `I` | `Qwen3-1.7B` | LangGraph refined workflow planner | `1.7B`에서 refined workflow 설정의 효과 확인 |
| `J` | `Qwen3-0.6B` | LangGraph refined workflow planner | `0.6B`에서 refined workflow 설정의 효과 확인 |

`I/J`는 version sweep 비교가 아니라, refined workflow를 고정한 독립 실행 조건으로 해석합니다.

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

- `A` vs `B` vs `D`: `0.6B`, `1.7B`, `14B-AWQ` direct 사이에서 model size에 따른 planning gap은 어떻게 나타나는가
- `A` vs `G`, `B` vs `C`, `D` vs `H`: 각 model size에서 `direct` 대비 `structured` prompting은 어떤 변화를 만드는가
- `E` vs `B/C`: `1.7B`에서 workflow-based system design은 direct/structured 대비 추가 개선을 주는가
- `F` vs `A/G`: `0.6B` 같은 compact model에서 workflow-based system design은 direct/structured 대비 더 큰 효과를 주는가
- `D/H` vs `A/B/C/E/F/G`: stronger reference 대비 compact model의 planning weakness와 intervention 효과는 어디서 갈리는가


## 추가 연구용 메타데이터

`results.jsonl`의 `metadata`에는 아래 필드가 저장됩니다.

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

Refined workflow 조건(`I`, `J`)도 동일한 workflow 메타데이터 필드를 저장합니다.



### Experiment

- Main result block: `10 personas x A/B/C/D/E/F = 60 outputs`
- Structured ablation block: `10 personas x G/H = 20 outputs`
- Additional refined workflow block: `10 personas x I/J = 20 outputs`
- Full result block with ablations and extra experiments: `100 outputs`

보고서 본문은 `model size`, `prompting strategy` (`direct` vs. `structured`), 그리고 `workflow-based system design`의 효과를 함께 읽을 수 있도록 `A/B/C/D/E/F` main comparison을 기준으로 구성하고, `G/H`는 structured prompting의 capacity-boundary ablation으로, `I/J`는 과제 외 추가 실험으로 별도 해석하는 방향으로 잡습니다.

`configs/models.yaml`의 기본값은 아래와 같습니다.

- `tiny = Qwen/Qwen3-0.6B`
- `small = Qwen/Qwen3-1.7B`
- `strong = Qwen/Qwen3-14B-AWQ`

즉 코드도 README와 동일한 실험 condition 라벨을 사용합니다.

## Working Environment

의존성 설치:

```bash
pip install -r requirements.txt
```

## 실행 명령

아래 스크립트 이름은 README의 `A/B/C/D/E/F/G/H/I/J` condition label과 동일합니다.

```bash
python src/load_personas.py
bash scripts/run_condition_a.sh
bash scripts/run_condition_b.sh
bash scripts/run_condition_c.sh
bash scripts/run_condition_d.sh
bash scripts/run_condition_e.sh
bash scripts/run_condition_f.sh
bash scripts/run_condition_g.sh
bash scripts/run_condition_h.sh
bash scripts/run_condition_i.sh
bash scripts/run_condition_j.sh
```

전체 실행:

```bash
bash scripts/run_all.sh
```

`run_all.sh`는 main comparison block인 `A-F`만 실행합니다.

## 평가 명령

LLM judge 평가:

```bash
python src/evaluate_llm_judge.py \
  --outputs outputs/condition_a/results.jsonl \
  --personas data/processed/personas_normalized.jsonl
```

자동 평가는 `LLM judge`만 사용하며, `1-10` 스케일을 사용합니다. 비판적 rubric은 [prompts/judge_rubric.txt]에, 관련 설정은 [configs/evaluation.yaml]에 있습니다.

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

**model size와 prompting strategy에 따른 planning 차이를 먼저 드러낸 뒤, workflow-based system design이 특히 compact model에서 그 한계를 어디까지 보완할 수 있는지 확인한다**
