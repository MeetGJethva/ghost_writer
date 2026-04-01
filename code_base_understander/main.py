import os
import sys
from code_base_understander.indexer import ProjectIndexer
from code_base_understander.query import ContextQuery
from code_base_understander.storage import load_skeleton, save_skeleton

from dotenv import load_dotenv
load_dotenv()

SKELETON_FILE = ".ctx_skeleton.json"


def main(project_dir: str, query: str, provider: str = "groq", model: str | None = None):
    skeleton_path = f"{project_dir}/{SKELETON_FILE}"

    # Build skeleton if it doesn't exist
    if not os.path.exists(skeleton_path):
        print(f"Indexing project: {project_dir}")
        skeleton = ProjectIndexer(project_dir).index()
        save_skeleton(skeleton, skeleton_path)
        print(f"Indexed {len(skeleton.files)} files. Stack: {', '.join(skeleton.tech_stack)}\n")
    else:
        print(f"Loading existing skeleton from {skeleton_path}\n")
        skeleton = load_skeleton(skeleton_path)

    # Query
    print(f"Query: {query} (Provider: {provider})\n")
    result = ContextQuery(skeleton, provider=provider, model=model).query(query)

    print(f"Summary: {result.summary}\n")
    print("=" * 60)

    for fc in result.files:
        print(f"\n>>> {fc.path}  [{fc.role}]")
        print(f"    Why: {fc.why_relevant}")
        print("-" * 60)
        print(fc.content[:300])

    return {
        "skeleton_path": skeleton_path,
        "output_dir": project_dir,
        "related_files": result.files,
        "summary": result.summary,
    }



if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: uv run main.py <project_dir> <query>")
        print('Example: uv run main.py /tmp/test-ecommerce "add a cart page"')
        sys.exit(1)

    main(project_dir=sys.argv[1], query=sys.argv[2])