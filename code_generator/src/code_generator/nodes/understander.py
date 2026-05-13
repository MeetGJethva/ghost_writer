import os
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from code_generator.src.code_generator.nodes.state import PipelineState
from code_base_understander.main import main as understand_codebase

class QueryIntent(BaseModel):
    """Classifies whether a user query requires code modifications or is just a question."""
    requires_code_change: bool = Field(
        description=(
            "True if the user is requesting code to be written, modified, created, deleted, "
            "refactored, or updated in any way. False if the user is asking a question about "
            "the codebase, seeking an explanation, asking how something works, or requesting "
            "information without any code changes."
        )
    )
    reasoning: str = Field(description="Brief explanation of why this was classified as a code change or a question.")


def _classify_intent(user_query: str, conversation_history: str) -> QueryIntent:
    """
    Classify whether the user query requires code changes or is just a question.
    """
    llm = ChatGroq(
        model_name="llama-3.3-70b-versatile",
        groq_api_key=os.getenv("GROQ_API_KEY"),
        temperature=0,
    ).with_structured_output(QueryIntent)

    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are an intent classifier. Determine whether the user's query requires "
            "modifications to the codebase (writing, editing, creating, deleting, or refactoring code) "
            "or is simply a question seeking information/explanation about the codebase.\n\n"
            "Examples of QUESTIONS (requires_code_change = false):\n"
            "- 'How does the authentication flow work?'\n"
            "- 'What does the UserService class do?'\n"
            "- 'Explain the database schema'\n"
            "- 'Where is the cart logic implemented?'\n"
            "- 'What API endpoints are available?'\n\n"
            "Examples of CODE CHANGES (requires_code_change = true):\n"
            "- 'Add a delete button to the cart page'\n"
            "- 'Fix the bug in the login function'\n"
            "- 'Refactor the payment service'\n"
            "- 'Create a new API endpoint for orders'\n"
            "- 'Update the database model to include email'\n\n"
            "CONVERSATION HISTORY:\n{history}\n"
        )),
        ("user", "{query}"),
    ])

    chain = prompt | llm
    return chain.invoke({"query": user_query, "history": conversation_history})


def understander_node(state: PipelineState) -> PipelineState:
    """
    Node 1: Analyze the project codebase and classify intent.
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

        # Classify whether the query needs code changes
        intent = _classify_intent(
            state["user_query"],
            state.get("conversation_history", "")
        )
        print(f"🧠  Intent: requires_code_change={intent.requires_code_change} | {intent.reasoning}")

        return {
            **state,
            "skeleton_path": result["skeleton_path"],
            "output_dir": result["output_dir"],
            "related_files": related_files,
            "understanding_output": result.get("summary", ""),
            "requires_code_change": intent.requires_code_change,
        }
    except Exception as e:
        return {**state, "error": f"Understander failed: {str(e)}"}
