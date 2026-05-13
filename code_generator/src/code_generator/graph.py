"""
graph.py – LangGraph orchestration for the code generation pipeline.

Flow: START → orchestrator_node → (routing) → understander_node → code_generator_node → summarizer_node → END
"""

from langgraph.graph import StateGraph, START, END

from code_generator.src.code_generator.nodes import (
    PipelineState,
    orchestrator_node,
    understander_node,
    code_generator_node,
    summarizer_node,
    # tester_node
)


# ── Routing Logic ─────────────────────────────────────────────────────────────

def route_after_orchestrator(state: PipelineState) -> str:
    if state.get("error"):
        return "summarizer"
    if not state.get("selected_project"):
        return "summarizer"
    return "understander"


def route_after_understander(state: PipelineState) -> str:
    """Route based on intent: questions skip the code generator."""
    if state.get("error"):
        return "summarizer"
    if not state.get("requires_code_change", True):
        print("📋  Question-only query — skipping code generator, going to summarizer.")
        return "summarizer"
    return "code_generator"


# ── Build the graph ───────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    builder = StateGraph(PipelineState)

    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("understander", understander_node)
    builder.add_node("code_generator", code_generator_node)
    # builder.add_node("tester", tester_node)
    builder.add_node("summarizer", summarizer_node)

    builder.add_edge(START, "orchestrator")
    
    builder.add_conditional_edges(
        "orchestrator",
        route_after_orchestrator,
        {
            "understander": "understander",
            "summarizer": "summarizer"
        }
    )

    builder.add_conditional_edges(
        "understander",
        route_after_understander,
        {"summarizer": "summarizer", "code_generator": "code_generator"}
    )

    builder.add_edge("code_generator", "summarizer")
    builder.add_edge("summarizer", END)

    return builder.compile()


pipeline = build_graph()
