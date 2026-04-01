"""
main.py – Entry point for the code-generator pipeline.

Usage:
    python main.py \\
        --query "Create a Python calculator module with add/sub/mul/div" \\
        --skeleton path/to/skeleton.json \\
        --output-dir ./output
        --related-files path/to/related_files.json

Or with an inline JSON skeleton:
    python main.py \\
        --query "..." \\
        --skeleton-json '{"files": [...]}' \\
        --output-dir ./output
"""

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser(
        prog="code-generator",
        description="AI-powered code generation and testing pipeline",
    )
    parser.add_argument(
        "--query", "-q",
        required=True,
        help="Natural language description of what code to generate",
    )

    skeleton_group = parser.add_mutually_exclusive_group(required=True)
    skeleton_group.add_argument(
        "--skeleton", "-s",
        metavar="PATH",
        help="Path to a JSON file describing the project skeleton",
    )
    skeleton_group.add_argument(
        "--skeleton-json",
        metavar="JSON",
        help="Inline JSON string describing the project skeleton",
    )

    parser.add_argument(
        "--output-dir", "-o",
        default="./output",
        help="Directory where generated code will be written (default: ./output)",
    )
    return parser.parse_args()


def load_skeleton(args) -> dict:
    """Load skeleton from file path or inline JSON."""
    if args.skeleton:
        path = Path(args.skeleton)
        if not path.exists():
            print(f"❌ Skeleton file not found: {path}", file=sys.stderr)
            sys.exit(1)
        return json.loads(path.read_text(encoding="utf-8"))
    else:
        try:
            return json.loads(args.skeleton_json)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in --skeleton-json: {e}", file=sys.stderr)
            sys.exit(1)

from langsmith import traceable
from langsmith.run_helpers import get_current_run_tree
import os
@traceable(name="Code-Generation.main", run_type="chain")
def main():
    args = parse_args()
    skeleton = load_skeleton(args)
    output_dir = str(Path(args.output_dir).resolve())

    # Import here so dotenv is loaded first
    from code_generator.graph import pipeline

    print("\n" + "█" * 60)
    print(" CODE GENERATOR & TESTER PIPELINE")
    print("█" * 60)
    print(f"\n📋 Query      : {args.query}")
    print(f"📁 Output dir : {output_dir}")
    print(f"🗂  Skeleton   : {json.dumps(skeleton, indent=2)}\n")

    run_tree = get_current_run_tree()
    if run_tree is not None:
        project = os.getenv("LANGSMITH_PROJECT", "hierarchical-agent-system")
        print(f"[LangSmith] Trace → https://smith.langchain.com/o/~/projects/p/{project}/r/{run_tree.id}\n")
    else:
        print("[LangSmith] No run tree found. Run with LANGSMITH_TRACING=true to enable tracing.")

    related_files = {'agents/child_agent.py': """from langchain_core.prompts.chat import ChatPromptTemplate
from .state import AgentState
from langchain_groq import ChatGroq
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
import os


class ChildAgent:
    
    Base class for specialized child 
    
    def __init__(self, name: str, expertise: str, model_name: str = None):
        self.name = name
        self.expertise = expertise
        self.model_name = model_name or os.getenv("GROQ_MODEL", "qwen/qwen3-32b")
        self.llm = ChatGroq(
            model=self.model_name,
            temperature=0.5,
            max_tokens=1024,
            api_key=os.getenv("GROQ_API_KEY")
        )
        """, 
    
    'agents/master_agent.py': """from .state import AgentState
from langchain_groq import ChatGroq
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
import os

class MasterPlannerAgent:
    
    Master Planner Agent - Creates execution plans and coordinates child agents
    def __init__(self, model_name: str = None):
        model_name = model_name or os.getenv("GROQ_MODEL", "qwen/qwen3-32b")
        self.llm = ChatGroq(
            model=model_name,
            temperature=0.7,
            max_tokens=1024,
            api_key=os.getenv("GROQ_API_KEY")
        )
        
        self.system_prompt = You are a Master Planner Agent responsible for:
1. Analyzing complex tasks
2. Breaking them down into subtasks
3. Assigning subtasks to appropriate child agents
4. Synthesizing results into a final answer

Available Child Agents:
- ResearchAgent: Gathers information, conducts research, finds facts
- AnalysisAgent: Analyzes data, identifies patterns, draws conclusions
- WritingAgent: Creates written content, reports, summaries
- CalculationAgent: Performs calculations, mathematical operations
- ValidationAgent: Validates results, checks quality, verifies facts
- CodingAgent: Generates python code, implements test cases (using assert), and executes it to logically verify correctness. Use whenever python code writing or testing is needed.

For each task, create a plan with numbered subtasks. Specify which agent should handle each subtask.

Format your plan as:
PLAN:
1. [Agent Name] - [Subtask description]
2. [Agent Name] - [Subtask description]
...
    """, 

    'hierarchical_agent_system.py': """
Hierarchical Agent System using LangChain and LangGraph

This system implements a master planner agent that receives tasks,
creates execution plans, and delegates subtasks to specialized child agents.


from agents.coding_agent import CodingAgent
from agents.child_agent import ChildAgent
class HierarchicalAgentSystem:
    
    Main hierarchical agent system that orchestrates the master and child agents
    
    
    def __init__(self):
        # Initialize master planner
        self.master = MasterPlannerAgent()
        
        # Initialize child agents
        self.child_agents = {
            "research": ChildAgent(
                "ResearchAgent",
                "gathering information, conducting research, finding facts and data"
            ),
            "analysis": ChildAgent(
                "AnalysisAgent",
                "analyzing data, identifying patterns, drawing conclusions, making comparisons"
            ),
            "writing": ChildAgent(
                "WritingAgent",
                "creating written content, reports, summaries, documentation"
            ),
            "calculation": ChildAgent(
                "CalculationAgent",
                "performing calculations, mathematical operations, quantitative analysis"
            ),
            "validation": ChildAgent(
                "ValidationAgent",
                "validating results, checking quality, verifying facts and accuracy"
            ),
            "coding": CodingAgent()
        }
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        "Build the LangGraph workflow"
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("planner", self.master.create_plan)
        workflow.add_node("research_agent", self.child_agents["research"].execute)
        workflow.add_node("analysis_agent", self.child_agents["analysis"].execute)
        workflow.add_node("writing_agent", self.child_agents["writing"].execute)
        workflow.add_node("calculation_agent", self.child_agents["calculation"].execute)
        workflow.add_node("validation_agent", self.child_agents["validation"].execute)
        workflow.add_node("coding_agent", self.child_agents["coding"].execute)
        workflow.add_node("synthesizer", self.master.synthesize_results)
        
        # Define routing logic
        def route_to_agent(state: AgentState) -> str:
            "Route to the appropriate agent based on current subtask"
            if state["current_step"] >= len(state["subtasks"]):
                return "synthesizer"
            
            subtask = state["subtasks"][state["current_step"]]
            agent_name = subtask["agent"].lower()
            
            if "research" in agent_name:
                return "research_agent"
            elif "analysis" in agent_name:
                return "analysis_agent"
            elif "writing" in agent_name:
                return "writing_agent"
            elif "calculation" in agent_name:
                return "calculation_agent"
            elif "validation" in agent_name:
                return "validation_agent"
            elif "coding" in agent_name or "code" in agent_name:
                return "coding_agent"
            else:
                # Default to research if unclear
                return "research_agent"
        
        def check_completion(state: AgentState) -> str:
            "Check if all subtasks are completed"
            if state["current_step"] >= len(state["subtasks"]):
                return "done"
            return "continue"
        
        # Set entry point
        workflow.set_entry_point("planner")
        
        # Add edges from planner to routing
        workflow.add_conditional_edges(
            "planner",
            route_to_agent,
            {
                "research_agent": "research_agent",
                "analysis_agent": "analysis_agent",
                "writing_agent": "writing_agent",
                "calculation_agent": "calculation_agent",
                "validation_agent": "validation_agent",
                "coding_agent": "coding_agent",
                "synthesizer": "synthesizer"
            }
        )
        
        # Add edges from each agent back to routing
        for agent in ["research_agent", "analysis_agent", "writing_agent", 
                      "calculation_agent", "validation_agent", "coding_agent"]:
            workflow.add_conditional_edges(
                agent,
                route_to_agent,
                {
                    "research_agent": "research_agent",
                    "analysis_agent": "analysis_agent",
                    "writing_agent": "writing_agent",
                    "calculation_agent": "calculation_agent",
                    "validation_agent": "validation_agent",
                    "coding_agent": "coding_agent",
                    "synthesizer": "synthesizer"
                }
            )
        
        # Synthesizer leads to end
        workflow.add_edge("synthesizer", END)
        
        return workflow.compile()
    
    @traceable(name="HierarchicalAgentSystem.run", run_type="chain")
    def run(self, task: str) -> dict:
        "Execute a task through the hierarchical agent system.

        Each call is recorded as a top-level trace in LangSmith when
        LANGSMITH_TRACING=true is set in the environment.
        "
        initial_state = {
            "messages": [HumanMessage(content=task)],
            "task": task,
            "plan": "",
            "current_step": 0,
            "subtasks": [],
            "results": [],
            "next_agent": "",
            "final_answer": ""
        }

        print(f"\n{'='*80}")
        print(f"TASK: {task}")
        print(f"{'='*80}\n")

        # Log the LangSmith trace URL if tracing is active
        run_tree = get_current_run_tree()
        if run_tree is not None:
            project = os.getenv("LANGSMITH_PROJECT", "hierarchical-agent-system")
            print(f"[LangSmith] Trace → https://smith.langchain.com/o/~/projects/p/{project}/r/{run_tree.id}\n")

        # Run the graph
        result = self.graph.invoke(initial_state)

        return result


""", 
    'agents/state.py': """from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    task: str
    plan: str
    current_step: int
    subtasks: list[dict]
    results: list[dict]
    next_agent: str
    final_answer: str""", 
    
    }
    initial_state = {
        "user_query": args.query,
        "skeleton": skeleton,
        "output_dir": output_dir,
        "related_files": related_files,
        "generator_output": "",
        "test_result": "",
    }

    final_state = pipeline.invoke(initial_state)

    print("\n" + "█" * 60)
    print(" PIPELINE COMPLETE")
    print("█" * 60)
    print("\n📝 GENERATOR OUTPUT:")
    print(final_state.get("generator_output", "(none)"))
    print("\n🧪 TEST RESULT:")
    print(final_state.get("test_result", "(none)"))
    print("\n" + "█" * 60)

def load_skeleton(path):
    with open(path, 'r') as f:
        return json.load(f)
    

def acess_code_generator(query: str, skeleton: str, output_dir: str, related_files: dict):
    from code_generator.src.code_generator.graph import pipeline

    initial_state = {
        "user_query": query,
        "skeleton": load_skeleton(skeleton),
        "output_dir": output_dir,
        "related_files": related_files,
        "generator_output": "",
        "test_result": "",
    }

    final_state = pipeline.invoke(initial_state)
    # print(initial_state)
    print("\n" + "█" * 60)
    print(" PIPELINE COMPLETE")
    print("█" * 60)
    print("\n📝 GENERATOR OUTPUT:")
    print(final_state.get("generator_output", "(none)"))
    print("\n🧪 TEST RESULT:")
    print(final_state.get("test_result", "(none)"))
    print("\n" + "█" * 60)
    


if __name__ == "__main__":
    # print("Hello")
    # acess_code_generator(1,2,3,4)
    main()
