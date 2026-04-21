"""
graph.py – LangGraph orchestration for the code generation pipeline.

Flow: START → code_generator_node → (conditional) tester_node → END

State carries:
  - user_query:   original user requirements
  - skeleton:     project skeleton JSON dict
  - output_dir:   where generated code lives
  - related_files: dict of related files
  - generator_output: final message from CodeGeneratorAgent
  - test_result:  final report from TesterAgent
  - files_modified: list of files created/updated during generation
"""

from typing import Any, TypedDict, List

from langgraph.graph import StateGraph, START, END

from code_generator.src.code_generator.agents.code_generator_agent import CodeGeneratorAgent
from code_generator.src.code_generator.agents.tester_agent import TesterAgent


# ── Shared pipeline state ─────────────────────────────────────────────────────

class PipelineState(TypedDict):
    """State shared across all nodes in the pipeline."""
    user_query: str
    skeleton: dict[str, Any]
    output_dir: str
    generator_output: str    # populated after code_generator_node
    test_result: str         # populated after tester_node
    related_files: dict[str, str]
    conversation_history: str
    files_modified: List[str] # track what changed
    final_summary: str


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
    result = agent.run(
        user_query=state["user_query"],
        skeleton=state["skeleton"],
        output_dir=state["output_dir"],
        related_files=state["related_files"],
        conversation_history=state.get("conversation_history", ""),
    )
    
    output_text = result.get("content", "")
    modified = result.get("modified_files", [])

    print(f"Agent Output: {output_text[:100]}...")
    print(f"Files Modified: {len(modified)}")

    print("\n✅  Code generator finished.")
    return {
        **state, 
        "generator_output": output_text,
        "files_modified": modified
    }


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
        modified_files=state.get("files_modified", []),
    )

    print("\n✅  Tester finished.")
    return {**state, "test_result": result}


# ── Conditional Edge ──────────────────────────────────────────────────────────

def decide_to_test(state: PipelineState) -> str:
    """
    Determines whether to run the tester agent or skip to the end.
    Only run if files were actually modified.
    """
    modified = state.get("files_modified", [])
    if modified:
        print("🔍 Files modified. Proceeding to testing...")
        return "tester"
    else:
        print("🔍 No files modified. Skipping tests.")
        return END


# ── Build the graph ───────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """Construct and compile the LangGraph pipeline."""
    builder = StateGraph(PipelineState)

    builder.add_node("code_generator", code_generator_node)
    builder.add_node("tester", tester_node)

    builder.add_edge(START, "code_generator")
    
    # Conditional edge after code generation
    builder.add_conditional_edges(
        "code_generator",
        decide_to_test,
        {
            "tester": "tester",
            END: END
        }
    )
    
    builder.add_edge("tester", END)

    return builder.compile()


# Singleton compiled graph (imported by main.py)
pipeline = build_graph()
