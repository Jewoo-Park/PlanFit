from __future__ import annotations

import json
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


class WorkflowState(TypedDict, total=False):
    persona: Dict[str, Any]
    profile_summary: str
    goal_strategy: str
    draft_plan: str
    safety_review: str
    constraint_review: str
    tradeoff_review: str
    final_plan: str
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
    )


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
            if "STATUS: PASS" not in state.get(field_name, "").upper():
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
