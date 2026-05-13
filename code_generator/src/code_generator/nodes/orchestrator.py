import os
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from code_generator.src.code_generator.nodes.state import PipelineState

class SelectedProject(BaseModel):
    """Structured response from the LLM routing decision."""
    project_id: Optional[str] = Field(default=None, description="The UUID of the selected project, or None if no project matches.")
    project_name: Optional[str] = Field(default=None, description="The name of the selected project, or None if no project matches.")
    folder_path: Optional[str] = Field(default=None, description="The absolute folder path of the selected project, or None if no project matches.")
    reasoning: str = Field(description="Brief explanation of why this project was selected, or a natural response to the user's query if no project is matched.")


def orchestrator_node(state: PipelineState) -> PipelineState:
    """
    Node 0: Match user query to a project.
    """
    print("\n" + "═" * 60)
    print("🎯  ORCHESTRATOR – starting")
    print("═" * 60)

    try:
        llm = ChatGroq(
            model_name="llama-3.3-70b-versatile", 
            groq_api_key=os.getenv("GROQ_API_KEY"),
            temperature=0,
        ).with_structured_output(SelectedProject)

        project_list_str = "\n".join([
            f"- ID: {p['id']}\n  Name: {p['name']}\n  Folder: {p['folder_path']}\n  Keywords: {p['keywords']}\n  Description: {p['description']}"
            for p in state["projects"]
        ])

        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are an intelligent orchestrator. Your job is to match a user query to the most appropriate project "
                "from the list provided. Each project has a name, description, keywords, and folder path.\n\n"
                "0. CONVERSATION HISTORY:\n{history}\n\n"
                "1. PROJECT LIST:\n{projects}\n\n"
                "Give natural response to normal queries and if user query is related to any of the projects, return the project_id.\n"
                "NEVER assume any folder path other than the ones provided in the project list.\n"
                "NEVER assume any project name other than the ones provided in the project list.\n"
                "IF user query is not related to any of the projects or neutral, return None as project_id.\n"
            )),
            ("user", "{query}"),
        ])

        chain = prompt | llm
        selection: SelectedProject = chain.invoke({
            "projects": project_list_str,
            "query": state["user_query"],
            "history": state.get("conversation_history", "")
        })

        if selection.project_id:
            # Find the full project dict
            selected = next((p for p in state["projects"] if str(p["id"]) == str(selection.project_id)), None)
            return {
                **state,
                "selected_project": selected,
                "selection_reasoning": selection.reasoning
            }
        else:
            return {
                **state,
                "selection_reasoning": selection.reasoning,
                "final_summary": selection.reasoning
            }

    except Exception as e:
        return {**state, "error": f"Orchestrator failed: {str(e)}"}
