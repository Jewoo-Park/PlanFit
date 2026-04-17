from __future__ import annotations

import json
import re
from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, START, StateGraph

from prompt_builder import build_prompt_from_key
from utils import strip_think_blocks


WORKFLOW_NODE_SPECS = [
    ("profile_extractor", "workflow_profile_extractor", "profile_summary"),
    ("goal_prioritizer", "workflow_goal_prioritizer", "goal_strategy"),
    ("draft_planner", "workflow_draft_planner", "draft_plan"),
    ("safety_checker", "workflow_safety_checker", "safety_review"),
    ("constraint_checker", "workflow_constraint_checker", "constraint_review"),
    ("tradeoff_checker", "workflow_tradeoff_checker", "tradeoff_review"),
    ("reviser_formatter", "workflow_reviser_formatter", "final_plan"),
]
BASE_WORKFLOW_NODE_SPECS = WORKFLOW_NODE_SPECS[:-1]
FINAL_NODE_SPEC = WORKFLOW_NODE_SPECS[-1]
REPAIR_NODE_SPEC = ("repair_planner", "workflow_repair_planner", "draft_plan")
CHECKER_FIELDS = {
    "safety_checker": "safety_review",
    "constraint_checker": "constraint_review",
    "tradeoff_checker": "tradeoff_review",
}
CHECKER_NODE_SPECS = [spec for spec in BASE_WORKFLOW_NODE_SPECS if spec[0] in CHECKER_FIELDS]
INITIAL_WORKFLOW_NODE_SPECS = [spec for spec in BASE_WORKFLOW_NODE_SPECS if spec[0] not in CHECKER_FIELDS]
DYNAMIC_FIXER_NODE_SPECS = [
    ("safety_fixer", "workflow_safety_fixer", "draft_plan"),
    ("constraint_fixer", "workflow_constraint_fixer", "draft_plan"),
    ("tradeoff_fixer", "workflow_tradeoff_fixer", "draft_plan"),
]
DYNAMIC_FIXER_BY_CHECKER = {
    "safety_checker": DYNAMIC_FIXER_NODE_SPECS[0],
    "constraint_checker": DYNAMIC_FIXER_NODE_SPECS[1],
    "tradeoff_checker": DYNAMIC_FIXER_NODE_SPECS[2],
}
DYNAMIC_FINAL_NODE_SPEC = ("dynamic_formatter", "workflow_dynamic_formatter", "final_plan")
LOCALIZED_WORKFLOW_NODE_SPECS = [
    ("profile_extractor", "workflow_profile_extractor", "profile_summary"),
    ("goal_prioritizer", "workflow_goal_prioritizer", "goal_strategy"),
    ("draft_planner", "workflow_draft_planner", "draft_plan"),
    ("safety_localized_checker", "workflow_safety_localized_checker", "safety_review"),
    ("constraint_localized_checker", "workflow_constraint_localized_checker", "constraint_review"),
    ("tradeoff_localized_checker", "workflow_tradeoff_localized_checker", "tradeoff_review"),
    ("localized_reviser_formatter", "workflow_localized_reviser_formatter", "final_plan"),
]
LOCALIZED_INITIAL_NODE_SPECS = LOCALIZED_WORKFLOW_NODE_SPECS[:3]
LOCALIZED_CHECKER_NODE_SPECS = LOCALIZED_WORKFLOW_NODE_SPECS[3:6]
LOCALIZED_FINAL_NODE_SPEC = LOCALIZED_WORKFLOW_NODE_SPECS[-1]
LOCALIZED_CHECKER_FIELDS = {
    "safety_localized_checker": "safety_review",
    "constraint_localized_checker": "constraint_review",
    "tradeoff_localized_checker": "tradeoff_review",
}


class WorkflowState(TypedDict, total=False):
    persona: Dict[str, Any]
    profile_summary: str
    goal_strategy: str
    draft_plan: str
    safety_review: str
    constraint_review: str
    tradeoff_review: str
    final_plan: str
    raw_review: str
    review_metric: str
    workflow_trace: List[Dict[str, str]]


def _append_trace(
    state: WorkflowState, node_name: str, prompt_key: str, output_text: str
) -> List[Dict[str, str]]:
    trace = list(state.get("workflow_trace", []))
    trace.append({"node": node_name, "prompt_key": prompt_key, "output": output_text})
    return trace


def _build_prompt(
    prompt_key: str,
    persona_value: Any,
    state: WorkflowState,
    prompts_cfg: Dict[str, Any],
) -> str:
    return build_prompt_from_key(
        prompt_key,
        prompts_cfg,
        persona=persona_value,
        profile_summary=state.get("profile_summary", ""),
        goal_strategy=state.get("goal_strategy", ""),
        draft_plan=state.get("draft_plan", ""),
        safety_review=state.get("safety_review", ""),
        constraint_review=state.get("constraint_review", ""),
        tradeoff_review=state.get("tradeoff_review", ""),
        raw_review=state.get("raw_review", ""),
        review_metric=state.get("review_metric", ""),
    )


def _status_is_pass(review_text: str) -> bool:
    normalized = (review_text or "").upper()
    return bool(re.search(r'(?:"STATUS"|STATUS)\s*[:=]\s*"?(PASS)\b', normalized))


class LangGraphWorkflowRunner:
    def __init__(
        self,
        *,
        generator: Any,
        prompts_cfg: Dict[str, Any],
        gen_cfg: Dict[str, Any],
        workflow_cfg: Dict[str, Any] | None = None,
    ) -> None:
        self.generator = generator
        self.prompts_cfg = prompts_cfg
        self.gen_cfg = dict(gen_cfg)
        self.workflow_cfg = dict(workflow_cfg or {})
        self.configured_mode = bool(self.workflow_cfg)
        self.max_revision_loops = max(0, int(self.workflow_cfg.get("max_revision_loops", 0)))
        self.strip_think = bool(self.workflow_cfg.get("strip_think_blocks", False))
        self.use_full_persona_context = bool(self.workflow_cfg.get("use_full_persona_context", False))
        self.node_generation_overrides = {
            str(node_name): dict(overrides or {})
            for node_name, overrides in (self.workflow_cfg.get("node_generation_overrides") or {}).items()
        }

        if self.configured_mode:
            self.node_order = [spec[0] for spec in BASE_WORKFLOW_NODE_SPECS] + [
                REPAIR_NODE_SPEC[0],
                FINAL_NODE_SPEC[0],
            ]
            self.prompt_keys = {
                node_name: prompt_key
                for node_name, prompt_key, _ in BASE_WORKFLOW_NODE_SPECS + [REPAIR_NODE_SPEC, FINAL_NODE_SPEC]
            }
        else:
            self.node_order = [spec[0] for spec in WORKFLOW_NODE_SPECS]
            self.prompt_keys = {
                node_name: prompt_key for node_name, prompt_key, _ in WORKFLOW_NODE_SPECS
            }

        self.graph = self._compile_graph()

    def _persona_prompt_value(self, persona: Dict[str, Any]) -> Any:
        if not self.use_full_persona_context:
            return persona
        return json.dumps(persona, ensure_ascii=False, indent=2)

    def _gen_cfg_for_node(self, node_name: str) -> Dict[str, Any]:
        cfg = dict(self.gen_cfg)
        cfg.update(self.node_generation_overrides.get(node_name, {}))
        return cfg

    def _clean_output(self, text: str) -> str:
        if not self.strip_think:
            return (text or "").strip()
        return strip_think_blocks(text)

    def _run_node(self, state: WorkflowState, node_name: str, prompt_key: str, output_field: str) -> str:
        persona_value = self._persona_prompt_value(state["persona"])
        prompt = _build_prompt(prompt_key, persona_value, state, self.prompts_cfg)
        output_text = self.generator.generate(prompt, self._gen_cfg_for_node(node_name))
        cleaned_output = self._clean_output(output_text)
        state[output_field] = cleaned_output
        state["workflow_trace"] = _append_trace(state, node_name, prompt_key, cleaned_output)
        return cleaned_output

    def _make_legacy_node(self, node_name: str, prompt_key: str, output_field: str):
        def node(state: WorkflowState) -> Dict[str, Any]:
            persona = state["persona"]
            prompt = _build_prompt(prompt_key, persona, state, self.prompts_cfg)
            output_text = self.generator.generate(prompt, self.gen_cfg)
            return {
                output_field: output_text,
                "workflow_trace": _append_trace(state, node_name, prompt_key, output_text),
            }

        return node

    def _make_configured_node(self, node_name: str, prompt_key: str, output_field: str):
        def node(state: WorkflowState) -> Dict[str, Any]:
            local_state: WorkflowState = dict(state)
            output_text = self._run_node(local_state, node_name, prompt_key, output_field)
            return {
                output_field: output_text,
                "workflow_trace": local_state["workflow_trace"],
            }

        return node

    def _compile_graph(self):
        graph = StateGraph(WorkflowState)
        if self.configured_mode:
            node_specs = BASE_WORKFLOW_NODE_SPECS
            make_node = self._make_configured_node
        else:
            node_specs = WORKFLOW_NODE_SPECS
            make_node = self._make_legacy_node

        for node_name, prompt_key, output_field in node_specs:
            graph.add_node(node_name, make_node(node_name, prompt_key, output_field))

        graph.add_edge(START, node_specs[0][0])
        for idx in range(len(node_specs) - 1):
            graph.add_edge(node_specs[idx][0], node_specs[idx + 1][0])
        graph.add_edge(node_specs[-1][0], END)
        return graph.compile()

    def _current_checker_failures(self, state: WorkflowState) -> List[str]:
        failures: List[str] = []
        for node_name, field_name in CHECKER_FIELDS.items():
            if not _status_is_pass(state.get(field_name, "")):
                failures.append(node_name)
        return failures

    def _run_legacy(self, persona: Dict[str, Any]) -> Dict[str, Any]:
        state = self.graph.invoke({"persona": persona, "workflow_trace": []})
        caught_by_nodes = [
            node_name
            for node_name, field_name in CHECKER_FIELDS.items()
            if "STATUS: PASS" not in state.get(field_name, "").upper()
        ]
        return {
            "profile_summary": state.get("profile_summary", ""),
            "goal_strategy": state.get("goal_strategy", ""),
            "draft_plan": state.get("draft_plan", ""),
            "safety_review": state.get("safety_review", ""),
            "constraint_review": state.get("constraint_review", ""),
            "tradeoff_review": state.get("tradeoff_review", ""),
            "final_plan": state.get("final_plan", ""),
            "workflow_trace": state.get("workflow_trace", []),
            "model_calls": len(self.node_order),
            "revision_loops": 1,
            "checker_fail_count": len(caught_by_nodes),
            "caught_by_node": caught_by_nodes or ["not_caught"],
            "remaining_fail_nodes": caught_by_nodes or ["resolved"],
        }

    def _run_configured(self, persona: Dict[str, Any]) -> Dict[str, Any]:
        state: WorkflowState = self.graph.invoke({"persona": persona, "workflow_trace": []})

        remaining_failures = self._current_checker_failures(state)
        caught_by_nodes = set(remaining_failures)
        revision_loops = 0

        while remaining_failures and revision_loops < self.max_revision_loops:
            revision_loops += 1
            self._run_node(state, *REPAIR_NODE_SPEC)
            for node_spec in CHECKER_NODE_SPECS:
                self._run_node(state, *node_spec)
            remaining_failures = self._current_checker_failures(state)
            caught_by_nodes.update(remaining_failures)

        self._run_node(state, *FINAL_NODE_SPEC)

        return {
            "profile_summary": state.get("profile_summary", ""),
            "goal_strategy": state.get("goal_strategy", ""),
            "draft_plan": state.get("draft_plan", ""),
            "safety_review": state.get("safety_review", ""),
            "constraint_review": state.get("constraint_review", ""),
            "tradeoff_review": state.get("tradeoff_review", ""),
            "final_plan": state.get("final_plan", ""),
            "workflow_trace": state.get("workflow_trace", []),
            "model_calls": len(state.get("workflow_trace", [])),
            "revision_loops": revision_loops,
            "checker_fail_count": len(remaining_failures),
            "caught_by_node": sorted(caught_by_nodes) or ["not_caught"],
            "remaining_fail_nodes": remaining_failures or ["resolved"],
        }

    def run(self, persona: Dict[str, Any]) -> Dict[str, Any]:
        if not self.configured_mode:
            return self._run_legacy(persona)
        return self._run_configured(persona)


class DynamicMultiAgentWorkflowRunner:
    def __init__(
        self,
        *,
        generator: Any,
        prompts_cfg: Dict[str, Any],
        gen_cfg: Dict[str, Any],
        workflow_cfg: Dict[str, Any] | None = None,
    ) -> None:
        self.generator = generator
        self.prompts_cfg = prompts_cfg
        self.gen_cfg = dict(gen_cfg)
        self.workflow_cfg = dict(workflow_cfg or {})
        self.max_revision_loops = max(0, int(self.workflow_cfg.get("max_revision_loops", 2)))
        self.strip_think = bool(self.workflow_cfg.get("strip_think_blocks", False))
        self.use_full_persona_context = bool(self.workflow_cfg.get("use_full_persona_context", False))
        self.use_final_formatter = bool(self.workflow_cfg.get("use_final_formatter", False))
        self.node_generation_overrides = {
            str(node_name): dict(overrides or {})
            for node_name, overrides in (self.workflow_cfg.get("node_generation_overrides") or {}).items()
        }
        node_specs = INITIAL_WORKFLOW_NODE_SPECS + CHECKER_NODE_SPECS + DYNAMIC_FIXER_NODE_SPECS
        if self.use_final_formatter:
            node_specs = node_specs + [DYNAMIC_FINAL_NODE_SPEC]
        self.node_order = [spec[0] for spec in node_specs]
        self.prompt_keys = {node_name: prompt_key for node_name, prompt_key, _ in node_specs}

    def _persona_prompt_value(self, persona: Dict[str, Any]) -> Any:
        if not self.use_full_persona_context:
            return persona
        return json.dumps(persona, ensure_ascii=False, indent=2)

    def _gen_cfg_for_node(self, node_name: str) -> Dict[str, Any]:
        cfg = dict(self.gen_cfg)
        cfg.update(self.node_generation_overrides.get(node_name, {}))
        return cfg

    def _clean_output(self, text: str) -> str:
        if not self.strip_think:
            return (text or "").strip()
        return strip_think_blocks(text)

    def _run_node(self, state: WorkflowState, node_name: str, prompt_key: str, output_field: str) -> str:
        persona_value = self._persona_prompt_value(state["persona"])
        prompt = _build_prompt(prompt_key, persona_value, state, self.prompts_cfg)
        output_text = self.generator.generate(prompt, self._gen_cfg_for_node(node_name))
        cleaned_output = self._clean_output(output_text)
        state[output_field] = cleaned_output
        state["workflow_trace"] = _append_trace(state, node_name, prompt_key, cleaned_output)
        return cleaned_output

    def _run_checkers(self, state: WorkflowState) -> Dict[str, str]:
        reviews: Dict[str, str] = {}
        for node_name, prompt_key, output_field in CHECKER_NODE_SPECS:
            reviews[node_name] = self._run_node(state, node_name, prompt_key, output_field)
        return reviews

    def _current_checker_failures(self, state: WorkflowState) -> List[str]:
        failures: List[str] = []
        for node_name, field_name in CHECKER_FIELDS.items():
            if not _status_is_pass(state.get(field_name, "")):
                failures.append(node_name)
        return failures

    def run(self, persona: Dict[str, Any]) -> Dict[str, Any]:
        state: WorkflowState = {"persona": persona, "workflow_trace": []}
        routing_trace: List[Dict[str, Any]] = []
        fixer_calls: List[str] = []

        for node_spec in INITIAL_WORKFLOW_NODE_SPECS:
            self._run_node(state, *node_spec)

        initial_draft_plan = state.get("draft_plan", "")
        self._run_checkers(state)

        remaining_failures = self._current_checker_failures(state)
        seen_failures = set(remaining_failures)
        routing_trace.append(
            {
                "stage": "initial_check",
                "failures": list(remaining_failures),
            }
        )

        revision_loops = 0
        while remaining_failures and revision_loops < self.max_revision_loops:
            revision_loops += 1
            active_fixers: List[str] = []
            failures_in = list(remaining_failures)

            for checker_name in failures_in:
                fixer_node = DYNAMIC_FIXER_BY_CHECKER[checker_name]
                active_fixers.append(fixer_node[0])
                fixer_calls.append(fixer_node[0])
                self._run_node(state, *fixer_node)

            self._run_checkers(state)
            remaining_failures = self._current_checker_failures(state)
            seen_failures.update(remaining_failures)
            routing_trace.append(
                {
                    "stage": f"revision_loop_{revision_loops}",
                    "failures_in": failures_in,
                    "fixers_called": active_fixers,
                    "failures_out": list(remaining_failures),
                }
            )

        if self.use_final_formatter:
            self._run_node(state, *DYNAMIC_FINAL_NODE_SPEC)
        else:
            state["final_plan"] = state.get("draft_plan", "")

        return {
            "profile_summary": state.get("profile_summary", ""),
            "goal_strategy": state.get("goal_strategy", ""),
            "initial_draft_plan": initial_draft_plan,
            "draft_plan": state.get("draft_plan", ""),
            "safety_review": state.get("safety_review", ""),
            "constraint_review": state.get("constraint_review", ""),
            "tradeoff_review": state.get("tradeoff_review", ""),
            "final_plan": state.get("final_plan", ""),
            "workflow_trace": state.get("workflow_trace", []),
            "model_calls": len(state.get("workflow_trace", [])),
            "revision_loops": revision_loops,
            "checker_fail_count": len(remaining_failures),
            "caught_by_node": sorted(seen_failures) or ["not_caught"],
            "remaining_fail_nodes": remaining_failures or ["resolved"],
            "initial_fail_nodes": routing_trace[0]["failures"] or ["resolved"],
            "routing_trace": routing_trace,
            "fixer_calls": fixer_calls,
            "fixers_triggered": sorted(set(fixer_calls)) or ["not_used"],
        }


class LocalizedPatchWorkflowRunner:
    def __init__(
        self,
        *,
        generator: Any,
        prompts_cfg: Dict[str, Any],
        gen_cfg: Dict[str, Any],
        workflow_cfg: Dict[str, Any] | None = None,
    ) -> None:
        self.generator = generator
        self.prompts_cfg = prompts_cfg
        self.gen_cfg = dict(gen_cfg)
        self.workflow_cfg = dict(workflow_cfg or {})
        self.strip_think = bool(self.workflow_cfg.get("strip_think_blocks", False))
        self.use_full_persona_context = bool(self.workflow_cfg.get("use_full_persona_context", False))
        self.postcheck_after_revision = bool(self.workflow_cfg.get("postcheck_after_revision", True))
        self.node_generation_overrides = {
            str(node_name): dict(overrides or {})
            for node_name, overrides in (self.workflow_cfg.get("node_generation_overrides") or {}).items()
        }
        self.localized_checker_names = {spec[0] for spec in LOCALIZED_CHECKER_NODE_SPECS}
        self.node_order = [spec[0] for spec in LOCALIZED_WORKFLOW_NODE_SPECS]
        self.prompt_keys = {node_name: prompt_key for node_name, prompt_key, _ in LOCALIZED_WORKFLOW_NODE_SPECS}
        self.prompt_keys["localized_review_normalizer"] = "workflow_localized_review_normalizer"

    def _persona_prompt_value(self, persona: Dict[str, Any]) -> Any:
        if not self.use_full_persona_context:
            return persona
        return json.dumps(persona, ensure_ascii=False, indent=2)

    def _gen_cfg_for_node(self, node_name: str) -> Dict[str, Any]:
        cfg = dict(self.gen_cfg)
        cfg.update(self.node_generation_overrides.get(node_name, {}))
        return cfg

    def _clean_output(self, text: str) -> str:
        if not self.strip_think:
            return (text or "").strip()
        return strip_think_blocks(text)

    def _run_node(self, state: WorkflowState, node_name: str, prompt_key: str, output_field: str) -> str:
        persona_value = self._persona_prompt_value(state["persona"])
        prompt = _build_prompt(prompt_key, persona_value, state, self.prompts_cfg)
        output_text = self.generator.generate(prompt, self._gen_cfg_for_node(node_name))
        cleaned_output = self._clean_output(output_text)
        stripped_output = cleaned_output.lstrip()
        if node_name in self.localized_checker_names and not (
            stripped_output.startswith("{") or stripped_output.upper().startswith("STATUS:")
        ):
            cleaned_output = self._normalize_localized_review(state, node_name, cleaned_output)
        state[output_field] = cleaned_output
        state["workflow_trace"] = _append_trace(state, node_name, prompt_key, cleaned_output)
        return cleaned_output

    def _normalize_localized_review(self, state: WorkflowState, node_name: str, raw_review: str) -> str:
        local_state: WorkflowState = dict(state)
        local_state["raw_review"] = raw_review
        local_state["review_metric"] = node_name.replace("_localized_checker", "").replace("_checker", "")
        persona_value = self._persona_prompt_value(state["persona"])
        prompt = _build_prompt("workflow_localized_review_normalizer", persona_value, local_state, self.prompts_cfg)
        normalized_text = self.generator.generate(
            prompt,
            self._gen_cfg_for_node("localized_review_normalizer"),
        )
        cleaned_normalized = self._clean_output(normalized_text)
        stripped_normalized = cleaned_normalized.lstrip()
        if stripped_normalized.startswith("{") or stripped_normalized.upper().startswith("STATUS:"):
            return cleaned_normalized
        return self._fallback_localized_review(local_state["review_metric"], raw_review)

    def _fallback_localized_review(self, review_metric: str, raw_review: str) -> str:
        text = " ".join((raw_review or "").split())
        upper_text = text.upper()
        if any(marker in upper_text for marker in ["NO ISSUES", "NO ISSUE", "ACCEPTABLE", "PASS"]):
            return "Status: PASS\nLocalized issues:\n- none"

        location_match = re.search(
            r"(Week\s*\d+\s*[,/-]?\s*Day\s*\d+|Week\s*\d+|Day\s*\d+|Goal and Constraint Summary|Progression Logic|Safety Notes|Trade-off Explanation)",
            text,
            flags=re.IGNORECASE,
        )
        location = location_match.group(1) if location_match else "Global"

        sentence_match = re.split(r"(?<=[.!?])\s+", text)
        why = sentence_match[0].strip() if sentence_match and sentence_match[0].strip() else "The review indicates a problem that needs a localized revision."
        evidence = text[:220].strip() or "The raw review flagged an issue in the current draft plan."
        patch_by_metric = {
            "safety": "Apply the smallest edit needed to remove the safety or recovery risk at the affected location.",
            "constraint": "Apply the smallest edit needed to satisfy the user's explicit schedule, preference, or limitation constraint at the affected location.",
            "tradeoff": "Apply the smallest edit needed to improve goal prioritization or week-to-week coherence at the affected location.",
        }
        required_patch = patch_by_metric.get(
            review_metric,
            "Apply the smallest edit needed to resolve the flagged issue at the affected location.",
        )
        return (
            "Status: FIX\n"
            "Localized issues:\n"
            f"- Location: {location}\n"
            f"  Why: {why}\n"
            f"  Evidence: {evidence}\n"
            f"  Required patch: {required_patch}"
        )

    def _run_checkers(self, state: WorkflowState) -> None:
        for node_spec in LOCALIZED_CHECKER_NODE_SPECS:
            self._run_node(state, *node_spec)

    def _current_checker_failures(self, state: WorkflowState) -> List[str]:
        failures: List[str] = []
        for node_name, field_name in LOCALIZED_CHECKER_FIELDS.items():
            if not _status_is_pass(state.get(field_name, "")):
                failures.append(node_name)
        return failures

    def run(self, persona: Dict[str, Any]) -> Dict[str, Any]:
        state: WorkflowState = {"persona": persona, "workflow_trace": []}

        for node_spec in LOCALIZED_INITIAL_NODE_SPECS:
            self._run_node(state, *node_spec)

        initial_draft_plan = state.get("draft_plan", "")
        self._run_checkers(state)
        initial_failures = self._current_checker_failures(state)
        caught_by_nodes = set(initial_failures)

        self._run_node(state, *LOCALIZED_FINAL_NODE_SPEC)

        remaining_failures = list(initial_failures)
        if self.postcheck_after_revision:
            state["draft_plan"] = state.get("final_plan", "")
            self._run_checkers(state)
            remaining_failures = self._current_checker_failures(state)
            caught_by_nodes.update(remaining_failures)

        return {
            "profile_summary": state.get("profile_summary", ""),
            "goal_strategy": state.get("goal_strategy", ""),
            "initial_draft_plan": initial_draft_plan,
            "draft_plan": initial_draft_plan,
            "safety_review": state.get("safety_review", ""),
            "constraint_review": state.get("constraint_review", ""),
            "tradeoff_review": state.get("tradeoff_review", ""),
            "final_plan": state.get("final_plan", ""),
            "workflow_trace": state.get("workflow_trace", []),
            "model_calls": len(state.get("workflow_trace", [])),
            "revision_loops": 1 if initial_failures else 0,
            "checker_fail_count": len(remaining_failures),
            "caught_by_node": sorted(caught_by_nodes) or ["not_caught"],
            "remaining_fail_nodes": remaining_failures or ["resolved"],
            "initial_fail_nodes": initial_failures or ["resolved"],
        }
