"""
orchestrator_agent.py – Orchestrator agent.

Given a user query and project list, this agent uses tools like list_projects
and list_jira_tasks to answer user queries or route user query to a matching project.
"""
import os
import json
from typing import Any, Dict, Optional

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from code_generator.src.code_generator.config import get_llm, MAX_AGENT_ITERATIONS
from code_generator.src.code_generator.tools.orchestrator_tools import ORCHESTRATOR_TOOLS, AVAILABLE_PROJECTS


class OrchestratorAgent:
    def __init__(self):
        self.llm = get_llm(temperature=0)
        self.agent = create_react_agent(
            model=self.llm,
            tools=ORCHESTRATOR_TOOLS,
        )

    def run(
        self,
        user_query: str,
        projects: list[dict],
        conversation_history: str = "",
    ) -> Dict[str, Any]:
        """
        Runs the Orchestrator agent to decide which project to work on or list Jira tasks.

        Args:
            user_query: The user's natural language input.
            projects: The list of project configurations available.
            conversation_history: Past context for memory.

        Returns:
            A dictionary containing:
              - project_id: The UUID of selected project, if selected.
              - reasoning: Agent's reasoning or answering text.
              - content: Final output message content from agent.
        """
        system_context = (
            f"You are an intelligent Orchestrator Agent.\n\n"
            f"YOUR GOALS:\n"
            f"1. Understand the user query.\n"
            f"2. If the user is asking to work on, modify, query or access a project, use 'list_projects' "
            f"to see what projects are available. If you find a matching project, call the 'select_project' tool.\n"
            f"3. If the user is asking about their current Jira tasks, Jira issues or work to-dos, use 'list_jira_tasks' to retrieve them, "
            f"then present them nicely to the user.\n"
            f"4. If the query is neutral or general, just have a conversation and return a natural response.\n\n"
            f"IMPORTANT RULES:\n"
            f"- NEVER assume project IDs or folder paths. ALWAYS use 'list_projects' to look them up if you need to select one.\n"
            f"- ONLY use 'select_project' when the user specifies they want to work on or modify an available project.\n"
            f"- If no project is requested or matched, DO NOT call 'select_project'. Just provide a helpful response directly.\n\n"
            f"0. CONVERSATION HISTORY:\n{conversation_history}\n\n"
            f"1. CURRENT QUERY:\n{user_query}"
        )

        # Store projects in the ContextVar so the tools can access them
        token = AVAILABLE_PROJECTS.set(projects)
        try:
            result = self.agent.invoke(
                {"messages": [HumanMessage(content=system_context)]},
                config={"recursion_limit": MAX_AGENT_ITERATIONS},
            )
        finally:
            AVAILABLE_PROJECTS.reset(token)

        messages = result.get("messages", [])
        
        # Parse the agent messages to look for a "select_project" tool call
        project_id = None
        reasoning = ""
        
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc["name"] == "select_project":
                        args = tc.get("args", {})
                        project_id = args.get("project_id")
                        reasoning = args.get("reasoning", "")

        final_content = messages[-1].content if messages else "Orchestrator executed successfully."
        
        # If no tool called select_project but final_content exists, that final_content serves as the reasoning/response.
        if not reasoning:
            reasoning = final_content

        return {
            "project_id": project_id,
            "reasoning": reasoning,
            "content": final_content
        }
