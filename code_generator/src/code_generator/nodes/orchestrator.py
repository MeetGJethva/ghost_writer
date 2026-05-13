import os
from typing import Optional
from code_generator.src.code_generator.nodes.state import PipelineState
from code_generator.src.code_generator.agents.orchestrator_agent import OrchestratorAgent


def orchestrator_node(state: PipelineState) -> PipelineState:
    """
    Node 0: Use OrchestratorAgent with tools (list_projects, list_jira_tasks) 
    to answer queries or match user query to an appropriate project.
    """
    print("\n" + "═" * 60)
    print("🎯  ORCHESTRATOR AGENT – starting")
    print("═" * 60)

    try:
        agent = OrchestratorAgent()
        
        # Run Orchestrator Agent
        result = agent.run(
            user_query=state["user_query"],
            projects=state["projects"],
            conversation_history=state.get("conversation_history", ""),
        )

        project_id = result.get("project_id")
        reasoning = result.get("reasoning", "")

        if project_id:
            # Find the full project dict matching the selected project_id
            selected = next((p for p in state["projects"] if str(p["id"]) == str(project_id)), None)
            
            if not selected:
                # Fallback if agent provided a non-existent project_id but selected something
                print(f"⚠️ Agent chose project_id '{project_id}', but it was not found in projects.")
                return {
                    **state,
                    "selection_reasoning": reasoning,
                    "final_summary": f"Agent attempted to select project {project_id}, but it was not found.",
                    "error": "Selected project not found."
                }

            print(f"🎯 Selected Project: {selected.get('name')} ({project_id})")
            print(f"🧠 Reasoning: {reasoning}")
            
            return {
                **state,
                "selected_project": selected,
                "selection_reasoning": reasoning
            }
        else:
            print("ℹ️ No project selected. Providing general response or tool output.")
            print(f"🧠 Reasoning: {reasoning}")
            
            return {
                **state,
                "selection_reasoning": reasoning,
                "final_summary": reasoning
            }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {**state, "error": f"Orchestrator agent failed: {str(e)}"}
