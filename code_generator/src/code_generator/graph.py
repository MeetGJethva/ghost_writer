"""
graph.py – LangGraph orchestration for the code generation pipeline.

Flow: START → orchestrator_node → (routing) → understander_node → code_generator_node → summarizer_node → END
"""

import os
import traceback
from typing import Any, TypedDict, List, Optional

from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from code_generator.src.code_generator.agents.code_generator_agent import CodeGeneratorAgent
from code_generator.src.code_generator.agents.tester_agent import TesterAgent
from code_generator.src.code_generator.config import get_llm
from code_base_understander.main import main as understand_codebase


# ── Structured Models ─────────────────────────────────────────────────────────

class SelectedProject(BaseModel):
    """Structured response from the LLM routing decision."""
    project_id: Optional[str] = Field(default=None, description="The UUID of the selected project, or None if no project matches.")
    project_name: Optional[str] = Field(default=None, description="The name of the selected project, or None if no project matches.")
    folder_path: Optional[str] = Field(default=None, description="The absolute folder path of the selected project, or None if no project matches.")
    reasoning: str = Field(description="Brief explanation of why this project was selected, or a natural response to the user's query if no project is matched.")


# ── Shared pipeline state ─────────────────────────────────────────────────────

class PipelineState(TypedDict):
    """State shared across all nodes in the pipeline."""
    # Inputs
    user_query: str
    projects: List[dict]
    conversation_history: str
    
    # Selection
    selected_project: Optional[dict]
    selection_reasoning: str
    
    # Analysis
    skeleton_path: str
    output_dir: str
    related_files: dict[str, str]
    understanding_output: str
    
    # Generation
    generator_output: str
    files_modified: List[str]
    
    # Results
    final_summary: str
    error: Optional[str]


# ── Node functions ────────────────────────────────────────────────────────────

def orchestrator_node(state: PipelineState) -> PipelineState:
    """
    Node 0: Match user query to a project.
    """
    print("\n" + "═" * 60)
    print("🎯  ORCHESTRATOR – starting")
    print("═" * 60)

    try:
        llm = ChatGroq(
            model_name="llama-3.1-8b-instant", 
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


def understander_node(state: PipelineState) -> PipelineState:
    """
    Node 1: Analyze the project codebase.
    """
    if state.get("error") or not state.get("selected_project"):
        return state

    print("\n" + "═" * 60)
    print("🔍  UNDERSTANDER – starting")
    print("═" * 60)

    try:
        project = state["selected_project"]
        result = understand_codebase(project["folder_path"], state["user_query"])
        
        related_files = {}
        for file in result["related_files"]:
            related_files[file.path] = file.content

        return {
            **state,
            "skeleton_path": result["skeleton_path"],
            "output_dir": result["output_dir"],
            "related_files": related_files,
            "understanding_output": result.get("summary", "")
        }
    except Exception as e:
        return {**state, "error": f"Understander failed: {str(e)}"}


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
        
        # Note: In a real scenario, we might want to load the skeleton dict correctly here
        # but the agent currently handles it via tools if needed. 
        # For this refactor, I'll pass the path if I can.
        
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


def summarizer_node(state: PipelineState) -> PipelineState:
    """
    Node 3: Synth results or report errors.
    """
    print("\n" + "═" * 60)
    print("📝  SUMMARIZER – starting")
    print("═" * 60)

    # If we already have a final summary (e.g. from no project matched) and no error, just return
    if state.get("final_summary") and not state.get("error"):
        return state

    try:
        llm = get_llm(temperature=0.3)
        
        if state.get("error"):
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a helpful assistant. Explain that an error occurred during the technical process and summarize what was attempted."),
                ("user", f"Task: {state['user_query']}\nError: {state['error']}\nPhase reached: {state.get('selection_reasoning', 'None')}")
            ])
            summary = llm.invoke(prompt.format_messages()).content
            return {**state, "final_summary": summary}

        agent_responses = {}
        if state.get("understanding_output"):
            agent_responses["CodeUnderstandingAgent"] = state["understanding_output"]
        if state.get("generator_output"):
            agent_responses["CodeGeneratorAgent"] = state["generator_output"]

        # if state.get("test_result"):
        #     agent_responses["TesterAgent"] = state["test_result"]

        responses_str = ""
        for agent, resp in agent_responses.items():
            responses_str += f"\n\n### {agent}\n{resp}"

        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are a Senior Project Manager summarizing the work of an AI engineer team.\n"
                "Provide a concise, professional summary of the work performed.\n"
                "SYNTHESIS REQUIREMENTS:\n"
                "- Acknowledge the core task completion.\n"
                "- Mention key files modified or created.\n"
                "- Use clean Markdown.\n"
                "- Keep it between 3-5 sentences.\n"
            )),
            ("user", f"**USER REQUEST:** {state['user_query']}\n\n**AGENT WORK LOGS:**{responses_str}"),
        ])
        
        result = llm.invoke(prompt.format_messages())
        return {**state, "final_summary": result.content}

    except Exception as e:
        # Extreme fallback
        return {**state, "final_summary": f"A critical error occurred: {str(e)}"}


# ── Routing Logic ─────────────────────────────────────────────────────────────

def route_after_orchestrator(state: PipelineState) -> str:
    if state.get("error"):
        return "summarizer"
    if not state.get("selected_project"):
        return "summarizer"
    return "understander"

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
        lambda x: "summarizer" if x.get("error") else "code_generator",
        {"summarizer": "summarizer", "code_generator": "code_generator"}
    )

    builder.add_edge("code_generator", "summarizer")
    builder.add_edge("summarizer", END)

    return builder.compile()


pipeline = build_graph()
