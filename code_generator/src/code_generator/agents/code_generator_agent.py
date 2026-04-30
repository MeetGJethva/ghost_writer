"""
code_generator_agent.py – CodeGenerator agent.

Given a user query and project skeleton JSON, this agent uses file tools
to write the full code into the output directory.
"""
import os
import json
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from code_generator.src.code_generator.config import code_generator_llm, MAX_AGENT_ITERATIONS
from code_generator.src.code_generator.tools.file_tools import FILE_TOOLS, WORKSPACE_ROOT


class CodeGeneratorAgent:
    def __init__(self):
        self.llm = code_generator_llm(temperature=0)
        # Using a higher recursion limit as editing/updating often requires 
        # more tool calls (read -> think -> write) than fresh creation.
        self.agent = create_react_agent(
            model=self.llm,
            tools=FILE_TOOLS,
        )

    def run(
        self,
        user_query: str,
        skeleton: dict[str, Any],
        related_files: dict[str, str],
        output_dir: str,
        conversation_history: str = "",
    ) -> dict[str, Any]:
        """
        Updates or creates project files.
        
        Args:
            user_query: The user's request (e.g., "Add a delete button to the cart").
            skeleton: The structural map of files targeted for this update.
            related_files: A dictionary of {path: content} for context/reference.
            output_dir: The active workspace directory.
            conversation_history: Previous conversation history for context.
            
        Returns:
            A dictionary containing:
              - content: The agent's final explanation/message.
              - modified_files: A list of paths that were actually written to.
        """
        skeleton_str = json.dumps(skeleton, indent=2)
        
        # Format the related files into a readable string for the System Prompt
        context_str = "\n---\n".join([f"FILE: {p}\nCONTENT:\n{c}" for p, c in related_files.items()])

        system_context = (
            f"You are an expert Senior Software Engineer capable of updating existing codebases.\n\n"
            f"WORKING DIRECTORY: {output_dir}\n\n"
            f"0. CONVERSATION HISTORY:\n{conversation_history}\n\n"
            f"1. CORE TASK:\n{user_query}\n\n"
            f"2. TARGET FILES (Skeleton):\nUse this to identify which files to create or modify:\n{skeleton_str}\n\n"
            f"3. RELATED CONTEXT (Read-Only):\nUse these files to understand dependencies/styles. Do NOT modify these unless they are also in the skeleton:\n{context_str}\n\n"
            f"INSTRUCTIONS:\n"
            f"- If a file in the skeleton already exists, READ it first using 'read_file' before updating.\n"
            f"- For existing files, prefer using 'replace_content' to make targeted changes (partial updates) instead of overwriting the whole file.\n"
            f"- Ensure new code is consistent with the 'Related Context' provided.\n"
            f"- Use 'create_file' for entirely new files or if a total rewrite is necessary.\n"
            f"- Always implement full, production-ready code. No placeholders.\n"
            f"- Confirm your work with 'list_directory' before finishing.\n"
        )

        # Set the workspace root for the tools to use (ensures paths are relative to output_dir)
        token = WORKSPACE_ROOT.set(os.path.abspath(output_dir))
        try:
            result = self.agent.invoke(
                {"messages": [HumanMessage(content=system_context)]},
                config={"recursion_limit": MAX_AGENT_ITERATIONS},
            )
        finally:
            WORKSPACE_ROOT.reset(token)

        messages = result.get("messages", [])
        
        # Track modified files by inspecting tool calls (both create and replace)
        modified_files = set()
        for m in messages:
            if hasattr(m, "tool_calls") and m.tool_calls:
                for tc in m.tool_calls:
                    if tc["name"] in ["create_file", "replace_content"]:
                        path = tc.get("args", {}).get("path")
                        if path:
                            modified_files.add(path)

        return {
            "content": messages[-1].content if messages else "Update failed.",
            "modified_files": list(modified_files)
        }