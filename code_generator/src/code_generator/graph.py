"""
graph.py – LangGraph orchestration for the code generation pipeline.

Flow: START → code_generator_node → tester_node → END

State carries:
  - user_query:   original user requirements
  - skeleton:     project skeleton JSON dict
  - output_dir:   where generated code lives
  - related_files: dict of related files
  - generator_output: final message from CodeGeneratorAgent
  - test_result:  final report from TesterAgent
"""

from typing import Any, TypedDict

from langgraph.graph import StateGraph, START, END

from code_generator.src.code_generator.agents.code_generator_agent import CodeGeneratorAgent
from code_generator.src.code_generator.agents.tester_agent import TesterAgent


# ── Shared pipeline state ─────────────────────────────────────────────────────

class PipelineState(TypedDict):
    """State shared across all nodes in the pipeline."""
    user_query: str
    skeleton: dict[str, Any]
    output_dir: str
    generator_output: str   # populated after code_generator_node
    test_result: str        # populated after tester_node
    related_files: dict[str, str]
    conversation_history: str


# ── Node functions ────────────────────────────────────────────────────────────

def code_generator_node(state: PipelineState) -> PipelineState:
    """
    Node 1: Run the CodeGeneratorAgent.
    Writes all code files into output_dir based on the skeleton.
    """
    print("\n" + "═" * 60)
    print("🔧  CODE GENERATOR AGENT – starting")
    print("═" * 60)

    agent = CodeGeneratorAgent()
    output = agent.run(
        user_query=state["user_query"],
        skeleton=state["skeleton"],
        output_dir=state["output_dir"],
        related_files=state["related_files"],
        conversation_history=state.get("conversation_history", ""),
    )
    print(f"Ouptput: {output}")

    print("\n✅  Code generator finished.")
    return {**state, "generator_output": output}


def tester_node(state: PipelineState) -> PipelineState:
    """
    Node 2: Run the TesterAgent.
    Reads generated files, runs tests, returns a PASS/FAIL report.
    """
    print("\n" + "═" * 60)
    print("🧪  TESTER AGENT – starting")
    print("═" * 60)

    agent = TesterAgent()
    result = agent.run(
        user_query=state["user_query"],
        output_dir=state["output_dir"],
        skeleton=state["skeleton"],
        modified_files=state["generator_output"],
    )

    print("\n✅  Tester finished.")
    return {**state, "test_result": result}


# ── Build the graph ───────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """Construct and compile the LangGraph pipeline."""
    builder = StateGraph(PipelineState)

    builder.add_node("code_generator", code_generator_node)
    builder.add_node("tester", tester_node)

    builder.add_edge(START, "code_generator")
    builder.add_edge("code_generator", "tester")
    builder.add_edge("tester", END)

    return builder.compile()


# Singleton compiled graph (imported by main.py)
pipeline = build_graph()
