# PlanFit

`PlanFit`은 4주 personalized hybrid training plan generation을 대상으로, 온디바이스급 소형 모델에 workflow 설계를 얹었을 때 planning quality의 격차를 얼마나 줄일 수 있는지 평가하는 실험 레포입니다.

이번 리스코프의 핵심 질문은 단순히 "작은 모델도 되나?"가 아니라, "on-device small model의 failure mode를 workflow가 얼마나 줄이고 local stronger reference와의 gap을 얼마나 회복하는가?"입니다.

## 현재 문서의 기준

이 README는 `Plan.md`에 정리된 **목표 실험 설계**를 기준으로 작성했습니다.  
현재 코드는 `A/B/C/D/E/F`까지 실행 가능하며, `C/F`는 `LangGraph` 기반 workflow planner로 연결되어 있습니다.

## Research Questions

1. Qwen3-1.7B 같은 on-device small model에 structured prompting과 workflow decomposition을 적용하면, direct prompting 대비 planning failure를 줄일 수 있는가?
2. `1.7B + workflow`는 local reference인 `Qwen3-8B-AWQ direct`와의 gap을 얼마나 줄일 수 있는가?
3. 이 workflow 효과는 더 작은 `Qwen3-0.6B`에서도 유지되는가, 아니면 capacity limit 때문에 빠르게 무너지는가?

## 고정할 실험 범위

- Task: 4주 personalized hybrid training plan generation
- Core rubric: `Constraint`, `Safety`, `Goal alignment`, `Trade-off`, `Coherence`
- Output schema: `Week / Day / Focus / Session / Duration / Intensity / Reason`
- Pilot personas: `P1 Junsu`, `P7 Soyeon`, `P8 Minseo`
- Evaluation protocol: blind human scoring + quantitative/qualitative analysis 분리

즉, rubric은 유지하고 model/system condition만 바꾸는 방향으로 갑니다.

## 메인 실험 조건

### Main conditions

| Condition | Model | System | Role |
| --- | --- | --- | --- |
| `A'` | `Qwen3-1.7B` | Direct planner | on-device small baseline |
| `B'` | `Qwen3-1.7B` | Structured planner | prompt structuring 효과 확인 |
| `C'` | `Qwen3-1.7B` | LangGraph workflow planner | 핵심 제안 조건 |
| `D'` | `Qwen3-8B-AWQ` | Direct planner | local stronger reference |

### Ablation conditions

| Condition | Model | System | Purpose |
| --- | --- | --- | --- |
| `E` | `Qwen3-0.6B` | Direct planner | 가장 작은 on-device baseline |
| `F` | `Qwen3-0.6B` | LangGraph workflow planner | 극소형 모델에서도 workflow가 먹히는지 확인 |

`0.6B structured`는 선택적 조건으로 남겨 두고, 우선은 `E/F`만으로 ablation을 구성합니다.

## Workflow 정의

`C'`의 핵심은 "멀티에이전트를 그냥 써본다"가 아니라, **같은 1.7B를 유지한 채 시스템 설계만 바꾸는 것**입니다.

권장 workflow는 아래 순서를 따릅니다.

1. `profile extractor`
2. `goal prioritizer`
3. `draft planner`
4. `safety checker`
5. `constraint checker`
6. `trade-off checker`
7. `reviser / formatter`

이 구조를 통해 다음 비교를 명확하게 만듭니다.

- `B'` vs `A'`: structured prompt만으로도 개선이 있는가
- `C'` vs `B'`: workflow가 prompt structuring을 넘어서는 추가 이득을 주는가
- `C'` vs `D'`: `1.7B + workflow`가 `8B-AWQ` reference에 얼마나 근접하는가
- `F` vs `E`: workflow 효과가 0.6B에서도 유지되는가

## 허점 분석 프레임

기존 PlanFit의 정성 분석 틀은 유지하고, actor만 새 설정에 맞게 바꿉니다.

| 기존 해석 축 | 새 해석 축 |
| --- | --- |
| small model 대표 실패 유형 | `0.6B / 1.7B direct` 대표 실패 유형 |
| reviser가 잘 고친 오류 | workflow가 잘 고친 오류 |
| reviser도 못 고친 오류 | workflow도 못 고친 오류 |
| strong direct 안정성 | `8B-AWQ direct`가 local reference로 더 안정적인가 |
| reasoning trace 반영 여부 | workflow trace / intermediate state가 제약을 제대로 반영하는가 |

권장 failure tagging은 아래와 같습니다.

| Failure type | Status label | Workflow-specific field |
| --- | --- | --- |
| Constraint violation | `fixed / partly fixed / not fixed` | `caught_by_node` |
| Safety issue | `fixed / partly fixed / not fixed` | `caught_by_node` |
| Goal misunderstanding | `fixed / not fixed` | `caught_by_node` |
| Trade-off failure | `fixed / partly fixed / not fixed` | `caught_by_node` |
| Long-term coherence issue | `fixed / not fixed` | `caught_by_node` |

`caught_by_node`는 `extractor / safety checker / constraint checker / trade-off checker / not caught`처럼 기록합니다.

## 평가 시트에 추가할 메타데이터

기존 점수 체계는 유지하되, workflow 해석을 위해 아래 필드를 함께 저장합니다.

- `model_family`
- `system_type`
- `model_calls`
- `total_tokens`
- `latency`
- `checker_fail_count`
- `revision_loops`
- `caught_by_node`
- `major_failure_mode`
- `fixed_by_workflow`

즉, 품질 점수만이 아니라 과정 비용까지 같이 비교합니다.

## 파일럿과 본실험

### Pilot

- Personas: `P1`, `P7`, `P8`
- Conditions: `A'`, `B'`, `C'`, `D'`, `E`, `F`
- Total outputs: `3 personas x 6 conditions = 18 outputs`

### Main experiment

- Main result block: `10 personas x A'/B'/C'/D' = 40 outputs`
- Extended ablation: pilot에서 `0.6B workflow`가 의미 있으면 `E/F`를 추가해 `+20 outputs`
- Full total with ablation: `60 outputs`

보고서 본문은 `A'/B'/C'/D'` 중심으로, `0.6B`는 appendix 또는 ablation section으로 두는 구성을 기본으로 합니다.

## 현재 코드베이스와의 매핑

현재 레포의 구현은 아직 legacy 구조를 따릅니다.

| Current code | Current meaning | Planned direction |
| --- | --- | --- |
| `A` | small direct planner | `A'`로 유지하되 small model을 `1.7B`로 교체 |
| `B` | small structured planner | `B'`로 유지하되 model을 `1.7B`로 교체 |
| `C` | small LangGraph workflow planner | `C'` 구현 완료 |
| `D` | strong direct planner | `D'` local stronger reference |
| `E` | tiny direct planner | `0.6B` ablation baseline |
| `F` | tiny LangGraph workflow planner | `0.6B` workflow ablation |

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

이 프로젝트의 최종 메시지는 "0.6B나 1.7B가 곧바로 8B급이다"가 아닙니다.  
더 안전한 주장은 아래와 같습니다.

> workflow가 on-device small model의 failure mode를 얼마나 줄이고, task-specific planning rubric에서 local `8B-AWQ` reference와의 gap을 얼마나 회복하는가

이 framing을 유지하면, 이번 프로젝트는 단순한 multi-agent 적용 사례가 아니라 **온디바이스 환경에서 시스템 설계가 model-size gap을 얼마나 메울 수 있는지**를 묻는 연구로 정리할 수 있습니다.
