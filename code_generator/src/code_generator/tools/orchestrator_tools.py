"""
orchestrator_tools.py – Agent tools for listing projects, tasks, and making a selection.
"""

import os
from contextvars import ContextVar
from langchain_core.tools import tool
from jira import JIRA
import json
from dotenv import load_dotenv

load_dotenv()
# ── Context Variable for Projects ─────────────────────────────────────────────────
# This context variable stores the list of all project dicts currently active.
# It is set in OrchestratorAgent.run before the agent starts its work.
AVAILABLE_PROJECTS = ContextVar("available_projects", default=[])


@tool
def list_projects() -> str:
    """
    List all software projects available in the system.
    Use this tool when you need to see names, descriptions, and folder paths of all
    available projects, in order to choose which one matches the user's query.
    """
    projects = AVAILABLE_PROJECTS.get()
    if not projects:
        return "No projects are currently loaded or available in the workspace context."
    
    project_list_str = "\n".join([
        f"- ID: {p.get('id')}\n  Name: {p.get('name')}\n  Folder: {p.get('folder_path')}\n  Keywords: {p.get('keywords')}\n  Description: {p.get('description')}"
        for p in projects
    ])
    return f"📋 AVAILABLE PROJECTS:\n{project_list_str}"


@tool
def list_jira_tasks() -> str:
    """
    Fetch and list the current Jira tasks assigned to you.
    Use this tool if the user asks about current tasks, issues, or to-do items on Jira.
    """
    try:
        # Accessing Jira using credentials matching those in jira_worker.py
        jira_url = os.getenv('JIRA_URL')
        jira_email = os.getenv('JIRA_EMAIL')
        jira_api_token = os.getenv('JIRA_TOKEN')
        
        jira = JIRA(server=jira_url, basic_auth=(jira_email, jira_api_token))
        current_tasks = jira.search_issues('assignee = currentUser()')
        
        if not current_tasks:
            return "No Jira tasks found assigned to you."

        tasks_str = []
        for issue in current_tasks:
            full_data = json.dumps(issue.raw['fields'], indent=4)
            tasks_str.append(f"- [{issue.key}] {issue.fields.summary}\n{full_data}")
        
        return "🔔 CURRENT JIRA TASKS:\n" + "\n".join(tasks_str)
    except Exception as e:
        return f"❌ Error listing Jira tasks: {str(e)}"


@tool
def select_project(project_id: str, reasoning: str) -> str:
    """
    Selects a specific project from the available projects to proceed with working on it.
    Call this tool ONLY when you identify that the user's request points to one of the 
    available projects, and you want to route execution to work on that project.
    
    Args:
        project_id: The exact ID/UUID of the project.
        reasoning: The brief reasoning for why this project was selected.
    """
    return f"✅ SUCCESS: Project '{project_id}' has been successfully selected. Reasoning: {reasoning}"


ORCHESTRATOR_TOOLS = [list_projects, list_jira_tasks, select_project]
