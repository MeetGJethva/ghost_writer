from __future__ import annotations
import os
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

from code_base_understander.models import FileContext, FileNode, ProjectSkeleton, QueryResult

from dotenv import load_dotenv
load_dotenv()


# Max files to return (keeps context window manageable)
MAX_FILES = 8
# Max file size to read in full (lines)
MAX_FILE_LINES = 600


def _read_file(root: str, rel_path: str) -> str:
    abs_path = Path(root) / rel_path
    try:
        lines = abs_path.read_text(errors="ignore").splitlines()
        if len(lines) > MAX_FILE_LINES:
            half = MAX_FILE_LINES // 2
            lines = lines[:half] + [f"\n... [{len(lines) - MAX_FILE_LINES} lines truncated] ...\n"] + lines[-half:]
        return "\n".join(lines)
    except OSError:
        return ""


def _skeleton_summary(skeleton: ProjectSkeleton) -> str:
    """Compact text representation of the skeleton for the LLM."""
    lines = [
        f"Tech stack: {', '.join(skeleton.tech_stack)}",
        f"Entry points: {', '.join(skeleton.entry_points) or 'none detected'}",
        "",
        "Route manifest:",
    ]
    for route, path in skeleton.route_manifest.items():
        lines.append(f"  {route} → {path}")

    lines += ["", "File inventory (path | role | key symbols):"]
    for rel, node in sorted(skeleton.files.items()):
        syms = ", ".join(node.symbols[:6])
        lines.append(f"  {rel} | {node.role} | {syms}")

    return "\n".join(lines)


def _build_selection_prompt(query: str, skeleton_text: str) -> str:
    return f"""You are a code navigation assistant. Given a developer query and a project skeleton, select the minimum set of files needed to fully answer the query.

PROJECT SKELETON:
{skeleton_text}

DEVELOPER QUERY:
{query}

Instructions:
- Return a JSON array of objects, each with:
    "path": relative file path (must exist in the skeleton)
    "why": one sentence explaining relevance
- Include files that need to be READ or MODIFIED, plus any files that define types/components they depend on.
- Do NOT include test files unless the query is specifically about tests.
- Limit to {MAX_FILES} files maximum. Prefer fewer, more precise files.
- Return ONLY the JSON array, no other text.

Example:
[
  {{"path": "src/routes/cart.ts", "why": "This is the router file where the cart endpoint must be added."}},
  {{"path": "src/models/product.ts", "why": "Cart items reference the Product type defined here."}}
]"""


class ContextQuery:
    """
    Layer 2: Uses the skeleton to navigate to the right files,
    then reads them fully and returns rich context for a given query.
    """

    def __init__(self, skeleton: ProjectSkeleton, provider: str = "groq", model: str | None = None):
        self.skeleton = skeleton
        self.provider = provider.lower()
        
        if self.provider == "groq":
            self.llm = ChatGroq(
                model=model or "llama-3.3-70b-versatile",
                groq_api_key=os.environ.get("GROQ_API_KEY"),
                temperature=0,
            )
        elif self.provider == "openrouter":
            self.llm = ChatOpenAI(
                model=model or "arcee-ai/trinity-large-preview:free",
                openai_api_key=os.environ.get("OPENROUTER_API_KEY"),
                openai_api_base="https://openrouter.ai/api/v1",
                temperature=0,
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def query(self, user_query: str) -> QueryResult:
        skeleton_text = _skeleton_summary(self.skeleton)
        
        retries = 5
        cut_size = 100  # initial cut

        while retries > 0:
            prompt = _build_selection_prompt(user_query, skeleton_text)
            print(f"llm token: {len(prompt)}")

            try:
                response = self.llm.invoke([HumanMessage(content=prompt)])
                raw = response.content.strip()
                break

            except Exception as e:
                error_msg = str(e).lower()

                if "413" in error_msg or "too large" in error_msg or "context_length_exceeded" in error_msg:
                    print(f"Context too large, cutting {cut_size} chars... ({retries} left)")

                    skeleton_text = skeleton_text[:-cut_size]

                    # 🔥 increase cut size exponentially
                    cut_size *= 4

                    retries -= 1
                    if retries == 0:
                        raise e
                else:
                    raise e

        selected = self._parse_selection(raw)

        # Expand: add direct dependencies of selected files (Layer 2 traversal)
        selected = self._expand_with_dependencies(selected)

        # Read file contents
        file_contexts = []
        for item in selected[:MAX_FILES]:
            path = item["path"]
            node = self.skeleton.get_node(path)
            if node is None:
                continue
            content = _read_file(self.skeleton.root, path)
            if not content:
                continue
            file_contexts.append(FileContext(
                path=path,
                role=node.role,
                content=content,
                why_relevant=item.get("why", ""),
            ))

        summary = self._build_summary(user_query, file_contexts)

        return QueryResult(
            query=user_query,
            files=file_contexts,
            summary=summary,
        )

    def _parse_selection(self, raw: str) -> list[dict]:
        import json
        # Strip markdown fences if present
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        try:
            result = json.loads(raw.strip())
            return result if isinstance(result, list) else []
        except json.JSONDecodeError:
            return []

    def _expand_with_dependencies(self, selected: list[dict]) -> list[dict]:
        """
        For each selected file, add its first-level imports if they are
        models, services, or config — these are almost always needed.
        """
        existing_paths = {item["path"] for item in selected}
        additions = []

        for item in selected:
            node = self.skeleton.get_node(item["path"])
            if node is None:
                continue
            for dep_path in self.skeleton.dependencies_of(item["path"]):
                if dep_path in existing_paths:
                    continue
                dep_node = self.skeleton.get_node(dep_path)
                if dep_node and dep_node.role in ("model", "service", "config"):
                    additions.append({
                        "path": dep_path,
                        "why": f"Dependency of {item['path']} (role: {dep_node.role})",
                    })
                    existing_paths.add(dep_path)

        return selected + additions

    def _build_summary(self, query: str, files: list[FileContext]) -> str:
        if not files:
            return "No relevant files found."
        paths = [f.path for f in files]
        roles = [f.role for f in files]
        return (
            f"Found {len(files)} relevant files for query: '{query}'. "
            f"Files: {', '.join(paths)}. "
            f"Roles: {', '.join(roles)}."
        )