from __future__ import annotations
import re
from pathlib import Path


# Lazy-loaded parsers per language
_parsers: dict[str, object] = {}


def _get_parser(lang: str):
    if lang not in _parsers:
        try:
            from tree_sitter_languages import get_parser
            _parsers[lang] = get_parser(lang)
        except Exception as e:
            print(f"[Parser Exception] : {e}")
            _parsers[lang] = None
    return _parsers[lang]


# --- Language detection ---

EXTENSION_MAP = {
    ".ts": "typescript", ".tsx": "typescript",
    ".js": "javascript", ".jsx": "javascript",
    ".py": "python",
}


def detect_language(path: str) -> str | None:
    return EXTENSION_MAP.get(Path(path).suffix.lower())


# --- Regex fallbacks (used when tree-sitter unavailable or parse fails) ---

def _regex_extract(source: str, lang: str) -> tuple[list[str], list[str], list[str]]:
    """Return (symbols, imports, exports) via regex."""
    symbols, imports, exports = [], [], []

    if lang == "python":
        symbols = re.findall(r"^(?:def|class)\s+(\w+)", source, re.MULTILINE)
        imports = re.findall(r"^from\s+(\.[\w./]+)\s+import|^import\s+(\.[\w./]+)", source, re.MULTILINE)
        imports = [i[0] or i[1] for i in imports if i[0] or i[1]]
    else:  # js/ts
        symbols = re.findall(
            r"(?:export\s+)?(?:function|class|const|let|var)\s+(\w+)", source
        )
        exports = re.findall(r"export\s+(?:default\s+)?(?:function|class|const)?\s*(\w+)", source)
        raw_imports = re.findall(r'(?:import|from)\s+["\']([^"\']+)["\']', source)
        imports = [i for i in raw_imports if i.startswith(".")]

    return symbols, imports, exports


# --- Tree-sitter extractors ---

def _extract_python(tree, source: str) -> tuple[list[str], list[str], list[str]]:
    symbols, imports = [], []
    src_bytes = source.encode()

    def walk(node):
        # 1. Extract Classes and Functions
        if node.type in ("function_definition", "class_definition"):
            for child in node.children:
                if child.type == "identifier":
                    symbols.append(src_bytes[child.start_byte:child.end_byte].decode())
                    break
        
        # 2. Extract "import x" or "import x.y"
        elif node.type == "import_statement":
            for child in node.children:
                if child.type == "dotted_name":
                    imports.append(src_bytes[child.start_byte:child.end_byte].decode())

        # 3. Extract "from .state import AgentState"
        elif node.type == "import_from_statement":
            module_name = ""
            for child in node.children:
                # This captures the dots (import_prefix) and the name (dotted_name)
                if child.type in ("import_prefix", "dotted_name", "relative_import"):
                    module_name += src_bytes[child.start_byte:child.end_byte].decode()
                # Stop when we hit the 'import' keyword
                if child.type == "import":
                    break
            if module_name:
                imports.append(module_name)

        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return symbols, imports, []


def _extract_js_ts(tree, source: str) -> tuple[list[str], list[str], list[str]]:
    symbols, imports, exports = [], [], []
    src_bytes = source.encode()

    def walk(node):
        t = node.type
        if t in (
            "function_declaration", "class_declaration",
            "lexical_declaration", "variable_declaration",
        ):
            for child in node.children:
                if child.type == "identifier":
                    symbols.append(src_bytes[child.start_byte:child.end_byte].decode())
                elif child.type in ("variable_declarator",):
                    for c2 in child.children:
                        if c2.type == "identifier":
                            symbols.append(src_bytes[c2.start_byte:c2.end_byte].decode())
                            break
        elif t == "import_statement":
            for child in node.children:
                if child.type == "string":
                    val = src_bytes[child.start_byte:child.end_byte].decode().strip("'\"")
                    if val.startswith("."):
                        imports.append(val)
        elif t == "export_statement":
            for child in node.children:
                if child.type == "identifier":
                    exports.append(src_bytes[child.start_byte:child.end_byte].decode())

        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return symbols, imports, exports


# --- Public API ---

def parse_file(abs_path: str) -> tuple[list[str], list[str], list[str]]:
    """
    Parse a source file.
    Returns (symbols, relative_imports, exports).
    """
    lang = detect_language(abs_path)
    if lang is None:
        return [], [], []

    try:
        source = Path(abs_path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return [], [], []

    parser = _get_parser(lang)
    if parser is None:
        return _regex_extract(source, lang)

    try:
        tree = parser.parse(source.encode())
        if lang == "python":
            return _extract_python(tree, source)
        else:
            return _extract_js_ts(tree, source)
    except Exception:
        return _regex_extract(source, lang)

if __name__ == "__main__":
    print(parse_file("/home/hexylon/Documents/meet/files/agents/coding_agent.py"))