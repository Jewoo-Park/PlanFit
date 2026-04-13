from __future__ import annotations

from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, START, StateGraph

from prompt_builder import build_prompt_from_key


WORKFLOW_NODE_SPECS = [
    ("profile_extractor", "workflow_profile_extractor", "profile_summary"),
    ("goal_prioritizer", "workflow_goal_prioritizer", "goal_strategy"),
    ("draft_planner", "workflow_draft_planner", "draft_plan"),
    ("safety_checker", "workflow_safety_checker", "safety_review"),
    ("constraint_checker", "workflow_constraint_checker", "constraint_review"),
    ("tradeoff_checker", "workflow_tradeoff_checker", "tradeoff_review"),
    ("reviser_formatter", "workflow_reviser_formatter", "final_plan"),
]
CHECKER_FIELDS = {
    "safety_checker": "safety_review",
    "constraint_checker": "constraint_review",
    "tradeoff_checker": "tradeoff_review",
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
    workflow_trace: List[Dict[str, str]]


def _append_trace(
    state: WorkflowState, node_name: str, prompt_key: str, output_text: str
) -> List[Dict[str, str]]:
    trace = list(state.get("workflow_trace", []))
    trace.append({"node": node_name, "prompt_key": prompt_key, "output": output_text})
    return trace


def _build_prompt(prompt_key: str, persona: Dict[str, Any], state: WorkflowState, prompts_cfg: Dict[str, Any]) -> str:
    return build_prompt_from_key(
        prompt_key,
        prompts_cfg,
        persona=persona,
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
    ) -> None:
        self.generator = generator
        self.prompts_cfg = prompts_cfg
        self.gen_cfg = gen_cfg
        self.node_order = [spec[0] for spec in WORKFLOW_NODE_SPECS]
        self.prompt_keys = {node_name: prompt_key for node_name, prompt_key, _ in WORKFLOW_NODE_SPECS}
        self.graph = self._compile_graph()

    def _make_node(self, node_name: str, prompt_key: str, output_field: str):
        def node(state: WorkflowState) -> Dict[str, Any]:
            persona = state["persona"]
            prompt = _build_prompt(prompt_key, persona, state, self.prompts_cfg)
            output_text = self.generator.generate(prompt, self.gen_cfg)
            return {
                output_field: output_text,
                "workflow_trace": _append_trace(state, node_name, prompt_key, output_text),
            }

        return node

    def _compile_graph(self):
        graph = StateGraph(WorkflowState)
        for node_name, prompt_key, output_field in WORKFLOW_NODE_SPECS:
            graph.add_node(node_name, self._make_node(node_name, prompt_key, output_field))

        graph.add_edge(START, WORKFLOW_NODE_SPECS[0][0])
        for idx in range(len(WORKFLOW_NODE_SPECS) - 1):
            graph.add_edge(WORKFLOW_NODE_SPECS[idx][0], WORKFLOW_NODE_SPECS[idx + 1][0])
        graph.add_edge(WORKFLOW_NODE_SPECS[-1][0], END)
        return graph.compile()

    def run(self, persona: Dict[str, Any]) -> Dict[str, Any]:
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
        }
