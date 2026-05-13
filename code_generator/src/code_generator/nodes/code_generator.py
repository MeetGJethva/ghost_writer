from code_generator.src.code_generator.nodes.state import PipelineState
from code_generator.src.code_generator.agents.code_generator_agent import CodeGeneratorAgent

def code_generator_node(state: PipelineState) -> PipelineState:
    """
    Node 2: Generate code changes.
    """
    if state.get("error") or not state.get("selected_project"):
        return state

    print("\n" + "═" * 60)
    print("🔧  CODE GENERATOR – starting")
    print("═" * 60)

    try:
        agent = CodeGeneratorAgent()
        result = agent.run(
            user_query=state["user_query"],
            skeleton={"files": []}, # Will be overridden by agent using output_dir/skeleton_path
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
    except Exception as e:
        return {**state, "error": f"Generator failed: {str(e)}"}
