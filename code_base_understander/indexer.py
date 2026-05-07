from __future__ import annotations
import json
import os
from pathlib import Path

from code_base_understander.models import FileNode, FileRole, ProjectSkeleton
from code_base_understander.parser import parse_file, detect_language

from dotenv import load_dotenv
load_dotenv()

# Files/dirs to always skip
IGNORE_DIRS = {
    ".git", "node_modules", ".next", "__pycache__", ".venv", "venv",
    "dist", "build", ".cache", "coverage", ".pytest_cache", ".mypy_cache",
}
IGNORE_EXTENSIONS = {".lock", ".log", ".map", ".ico", ".png", ".jpg", ".jpeg", ".svg", ".woff", ".woff2"}

# How many lines to read for role detection (avoid reading huge files fully)
ROLE_PEEK_LINES = 30


def _should_skip(path: Path) -> bool:
    for part in path.parts:
        if part in IGNORE_DIRS:
            return True
    if path.suffix in IGNORE_EXTENSIONS:
        return True
    return False


def _detect_role(rel_path: str, symbols: list[str], imports: list[str], peek: str) -> str:
    p = rel_path.lower().replace("\\", "/")
    scores = {role: 0 for role in [
        "entry_point", "route", "page", "component", 
        "service", "model", "config", "util", "test", "logic"
    ]}

    # --- 1. Path & Filename Analysis ---
    if any(x in p for x in ("main.", "index.", "app.py", "server.", "root.")):
        scores["entry_point"] += 5
    if "/routes/" in p or "/api/" in p or "route." in p:
        scores["route"] += 4
    if "/pages/" in p or "/screens/" in p or "page." in p:
        scores["page"] += 4
    if "/components/" in p or "/ui/" in p or "component." in p:
        scores["component"] += 4
    if "/models/" in p or "/schema" in p or "model." in p:
        scores["model"] += 4
    if "/services/" in p or "service." in p:
        scores["service"] += 4
    if "/utils/" in p or "/helpers/" in p or "util." in p:
        scores["util"] += 3
    if "test" in p or "spec." in p:
        scores["test"] += 10

    # --- 2. Symbol Intelligence ---
    for sym in symbols:
        s = sym.lower()
        # Database/Model patterns
        if any(x in s for x in ("schema", "table", "entity", "dto")):
            scores["model"] += 2
        # Frontend Component patterns
        if s.startswith(("use", "handle", "render")):
            scores["component"] += 1
        # API/Route patterns
        if s in ("get", "post", "put", "delete", "patch"):
            scores["route"] += 3
        # Logic/Agent patterns (Specific to your current projects)
        if any(x in s for x in ("agent", "executor", "planner", "chain")):
            scores["logic"] += 5

    # --- 3. Dependency/Import Analysis ---
    # This is powerful: a file importing 'react' is almost certainly a component
    all_imports = " ".join(imports).lower()
    if any(x in all_imports for x in ("react", "next/", "tailwind", "lucide")):
        scores["component"] += 3
    if any(x in all_imports for x in ("sqlalchemy", "prisma", "mongoose", "pydantic")):
        scores["model"] += 4
    if any(x in all_imports for x in ("fastapi", "express", "flask", "router")):
        scores["route"] += 3
    if any(x in all_imports for x in ("langchain", "openai", "anthropic", "langgraph")):
        scores["logic"] += 4

    # --- 4. Peek Content (Regex) ---
    if "export default" in peek or "return (" in peek or "JSX" in peek:
        scores["component"] += 2
    if "@app." in peek or "@router." in peek:
        scores["route"] += 5

    # Determine Winner
    winner = max(scores, key=scores.get)
    return winner if scores[winner] > 0 else "unknown"


def _detect_tech_stack(root: Path, all_files: list[Path]) -> list[str]:
    stack = []
    names = {f.name for f in all_files}
    rel_paths = {str(f.relative_to(root)) for f in all_files}

    # Package managers / frameworks via config files
    if "package.json" in names:
        try:
            pkg = json.loads((root / "package.json").read_text())
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            if "next" in deps:
                stack.append("Next.js")
            elif "react" in deps:
                stack.append("React")
            if "express" in deps:
                stack.append("Express")
            if "typescript" in deps or any(f.endswith(".ts") or f.endswith(".tsx") for f in rel_paths):
                stack.append("TypeScript")
            if "prisma" in deps:
                stack.append("Prisma")
            if "tailwindcss" in deps:
                stack.append("Tailwind CSS")
        except Exception:
            pass
        stack.append("Node.js")

    if "pyproject.toml" in names or "requirements.txt" in names or "setup.py" in names:
        stack.append("Python")
        try:
            content = (root / "pyproject.toml").read_text() if "pyproject.toml" in names else ""
            reqs = (root / "requirements.txt").read_text() if "requirements.txt" in names else ""
            combined = content + reqs
            if "fastapi" in combined.lower():
                stack.append("FastAPI")
            elif "django" in combined.lower():
                stack.append("Django")
            elif "flask" in combined.lower():
                stack.append("Flask")
        except Exception:
            pass

    return stack or ["Unknown"]


def _extract_route_manifest(files: dict[str, FileNode]) -> dict[str, str]:
    """
    Build route pattern → file path map.
    Handles Next.js file-based routing and FastAPI/Express patterns.
    """
    manifest = {}
    for path, node in files.items():
        if node.role not in ("route", "page"):
            continue

        # Next.js: pages/cart.tsx → /cart, app/cart/page.tsx → /cart
        p = path.replace("\\", "/")
        if "/pages/" in p:
            route = p.split("/pages/", 1)[1]
            route = route.rsplit(".", 1)[0]  # strip extension
            route = route.replace("/index", "").replace("index", "/")
            manifest[f"/{route}"] = path
        elif "/app/" in p and p.endswith("page.tsx") or p.endswith("page.ts"):
            route = p.split("/app/", 1)[1].replace("/page.tsx", "").replace("/page.ts", "")
            manifest[f"/{route}"] = path

        # Python: look for @router.get / @app.get in symbols
        for sym in node.symbols:
            if sym.startswith("router_") or sym.startswith("app_"):
                manifest[f"/{sym}"] = path

    return manifest


def _resolve_import(from_file: str, import_path: str, all_rel_paths: set[str]) -> str | None:
    """
    Resolve a relative import string to a known file in the project.
    from_file: e.g., 'agents/coding_agent.py'
    import_path: e.g., '.state' or 'agents.child_agent'
    """
    # Convert python dot notation to path notation
    # .state -> state, agents.child_agent -> agents/child_agent
    clean_import = import_path.lstrip('.')
    dot_count = len(import_path) - len(clean_import)
    
    import_as_path = clean_import.replace('.', os.sep)
    
    # Calculate base directory
    parts = Path(from_file).parts[:-1] # Remove filename
    
    # Handle relative dots (.. or .)
    if dot_count > 1:
        # Move up for each extra dot
        parts = parts[:-(dot_count-1)]
        
    # Construct potential relative path
    target_rel_path = os.path.join(*parts, import_as_path) if parts else import_as_path

    # Check against known project files with extensions
    for ext in (".py", ".ts", ".tsx", ".js", "/__init__.py"):
        candidate = target_rel_path + ext
        # Normalize slashes for comparison
        normalized_candidate = candidate.replace(os.sep, "/")
        for ref in all_rel_paths:
            if ref.replace(os.sep, "/") == normalized_candidate:
                return ref
                
    return None


class ProjectIndexer:
    """
    Builds a ProjectSkeleton (Layer 1) from a project directory.
    This is built once and stored. Subsequent queries use it as a navigation map.
    """

    def __init__(self, root: str):
        self.root = Path(root).resolve()

    def index(self) -> ProjectSkeleton:
        all_files = self._collect_files()
        tech_stack = _detect_tech_stack(self.root, all_files)

        files: dict[str, FileNode] = {}
        import_graph: dict[str, list[str]] = {}
        all_rel_paths: set[str] = set()

        for abs_path in all_files:
            rel = str(abs_path.relative_to(self.root))
            all_rel_paths.add(rel)

        for abs_path in all_files:
            rel = str(abs_path.relative_to(self.root))
            lang = detect_language(str(abs_path))

            if lang:
                symbols, raw_imports, exports = parse_file(str(abs_path))
            else:
                symbols, raw_imports, exports = [], [], []

            # Peek at first lines for role detection
            try:
                content = abs_path.read_text(errors="ignore")
                lines = content.splitlines()
                peek = "\n".join(lines[:ROLE_PEEK_LINES])
                size_lines = len(lines)
            except OSError:
                peek = ""
                size_lines = 0

            role = _detect_role(rel_path=rel, symbols=symbols, peek=peek, imports=raw_imports)

            # Resolve relative imports to known project files
            resolved_imports = []
            for imp in raw_imports:
                resolved = _resolve_import(rel, imp, all_rel_paths)
                if resolved:
                    resolved_imports.append(resolved)

            files[rel] = FileNode(
                path=rel,
                role=role,
                symbols=symbols,
                imports=resolved_imports,
                exports=exports,
                size_lines=size_lines,
            )
            import_graph[rel] = resolved_imports

        entry_points = [
            p for p, n in files.items() if n.role == "entry_point"
        ] or self._guess_entry_points(files)

        route_manifest = _extract_route_manifest(files)

        return ProjectSkeleton(
            root=str(self.root),
            tech_stack=tech_stack,
            entry_points=entry_points,
            route_manifest=route_manifest,
            files=files,
            import_graph=import_graph,
        )

    def _collect_files(self) -> list[Path]:
        result = []
        for path in sorted(self.root.rglob("*")):
            if path.is_file() and not _should_skip(path.relative_to(self.root)):
                result.append(path)
        return result

    def _guess_entry_points(self, files: dict[str, FileNode]) -> list[str]:
        candidates = ["src/main.py", "main.py", "app.py", "src/index.ts",
                      "src/index.js", "index.ts", "index.js", "app/page.tsx"]
        return [c for c in candidates if c in files]