from code_generator.src.code_generator.nodes.state import PipelineState
from code_generator.src.code_generator.agents.tester_agent import TesterAgent

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
