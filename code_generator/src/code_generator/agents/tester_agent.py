"""
tester_agent.py – Tester agent.

Given the output directory and original user requirements, this agent reads
the generated files, runs tests, and reports pass/fail.
"""
from typing import Any
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from code_generator.src.code_generator.config import get_llm, MAX_AGENT_ITERATIONS
from code_generator.src.code_generator.tools.test_tools import TEST_TOOLS
import json

class TesterAgent:
    """
    LangGraph ReAct agent that validates updates by running tests,
    checking integration with related files, and reporting regression status.
    """

    def __init__(self):
        self.llm = get_llm(temperature=0)
        self.agent = create_react_agent(
            model=self.llm,
            tools=TEST_TOOLS,
        )

    def run(
        self,
        user_query: str,
        skeleton: dict[str, Any],
        modified_files: str,
        output_dir: str,
    ) -> str:
        """
        Run the tester agent against the updated codebase.

        Args:
            user_query: Original user requirements for context.
            skeleton: Structural representation of the project.
            modified_files: The files that the code generator has modified or created.
            output_dir: The workspace directory.
        """
        skeleton_str = json.dumps(skeleton, indent=2)

        system_context = (
            f"You are an expert QA and Software Engineer.\n\n"
            f"WORKING DIRECTORY: {output_dir}\n\n"
            f"1. THE MISSION:\nVerify the update requested: {user_query}\n\n"
            f"2. PROJECT STRUCTURE (Skeleton):\nThis is the layout of the project, to help you navigate:\n{skeleton_str}\n\n"
            f"3. MODIFIED FILES:\nThese are the changes made by the Code Generator:\n{modified_files}\n\n"
            f"INSTRUCTIONS:\n"
            f"- FIRST: Use 'list_directory' to ensure all files in the skeleton exist.\n"
            f"- SECOND: Use 'read_file' on the updated files to check for logic errors or missing imports.\n"
            f"- THIRD: Check for existing tests. If they exist, run 'run_pytest'.\n"
            f"- FOURTH: If the update changed a logic/service file, write a targeted verification script "
            f"using 'run_python_code' that imports the updated module and asserts the new behavior.\n"
            f"- FINAL REPORT: Provide a PASS ✅ or FAIL ❌. If FAIL, be specific so the Generator can fix it."
        )

        result = self.agent.invoke(
            {"messages": [HumanMessage(content=system_context)]},
            config={"recursion_limit": MAX_AGENT_ITERATIONS},
        )

        messages = result.get("messages", [])
        return messages[-1].content if messages else "Testing failed to execute."