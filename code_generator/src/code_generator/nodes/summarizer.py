from langchain_core.messages import SystemMessage, HumanMessage
from code_generator.src.code_generator.nodes.state import PipelineState
from code_generator.src.code_generator.config import get_llm

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
            messages = [
                SystemMessage(content="You are a helpful assistant. Explain that an error occurred during the technical process and summarize what was attempted."),
                HumanMessage(content=f"Task: {state['user_query']}\nError: {state['error']}\nPhase reached: {state.get('selection_reasoning', 'None')}")
            ]
            summary = llm.invoke(messages).content
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

        # Use different prompts for question-only vs code-change flows
        is_question_only = not state.get("requires_code_change", True)

        if is_question_only:
            # Question-only flow: answer the question using file context
            related_files = state.get("related_files", {})
            files_context = "\n---\n".join([f"FILE: {p}\nCONTENT:\n{c}" for p, c in related_files.items()])

            messages = [
                SystemMessage(content=(
                    "You are a Senior Software Engineer answering a developer's question about a codebase.\n"
                    "Use the provided file contents to give a clear, accurate, and helpful answer.\n\n"
                    "RESPONSE REQUIREMENTS:\n"
                    "- Directly answer the question using information from the codebase.\n"
                    "- Reference specific files, functions, classes, or lines when relevant.\n"
                    "- Use clean Markdown formatting.\n"
                    "- Be concise but thorough.\n"
                    "- If the provided files don't contain enough information to fully answer, say so.\n"
                )),
                HumanMessage(content=(
                    f"**QUESTION:** {state['user_query']}\n\n"
                    f"**RELEVANT FILES:**\n{files_context}\n\n"
                    f"**CODEBASE SUMMARY:**{responses_str}"
                )),
            ]
        else:
            # Code-change flow: summarize the work done
            messages = [
                SystemMessage(content=(
                    "You are a Senior Project Manager summarizing the work of an AI engineer team.\n"
                    "Provide a concise, professional summary of the work performed.\n"
                    "SYNTHESIS REQUIREMENTS:\n"
                    "- Acknowledge the core task completion.\n"
                    "- Mention key files modified or created.\n"
                    "- Use clean Markdown.\n"
                    "- Keep it between 3-5 sentences.\n"
                )),
                HumanMessage(content=f"**USER REQUEST:** {state['user_query']}\n\n**AGENT WORK LOGS:**{responses_str}"),
            ]
        
        result = llm.invoke(messages)
        return {**state, "final_summary": result.content}

    except Exception as e:
        # Extreme fallback
        return {**state, "final_summary": f"A critical error occurred: {str(e)}"}
