from typing import TypedDict, List, Optional

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
    
    # Intent classification
    requires_code_change: bool
    
    # Generation
    generator_output: str
    files_modified: List[str]
    
    # Results
    final_summary: str
    error: Optional[str]
