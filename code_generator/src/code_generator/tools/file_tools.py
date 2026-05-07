"""
file_tools.py – File system tools for the CodeGenerator agent.

These tools allow the agent to create directories and files,
read existing files, and list directory contents.
They are automatically scoped to the active workspace to prevent
files from being created in the wrong directory.
"""

import os
from pathlib import Path
from contextvars import ContextVar
from langchain_core.tools import tool

# ── Path Scoping Logic ────────────────────────────────────────────────────────
# This context variable stores the absolute path to the target project root.
# It is set in CodeGeneratorAgent.run before the agent starts its work.
WORKSPACE_ROOT = ContextVar("workspace_root", default=None)

def resolve_path(path_str: str) -> Path:
    """
    Helper to resolve a path. If the path is relative, it is joined with the
    target project root (WORKSPACE_ROOT). If absolute, it stays absolute.
    """
    p = Path(path_str)
    if p.is_absolute():
        return p
    
    root = WORKSPACE_ROOT.get()
    if root:
        # Join relative paths with the project root
        return (Path(root) / p).resolve()
        
    # Fallback to local resolve if no workspace context is set
    return p.resolve()


@tool
def create_file(path: str, content: str) -> str:
    """
    Create or overwrite a file at the given path with the provided content.
    Parent directories are created automatically if they don't exist.

    Args:
        path: Relative path to the file within the project.
        content: The full content to write into the file.

    Returns:
        A success/error message string.
    """
    try:
        target = resolve_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"✅ File created: {target} ({len(content)} chars)"
    except Exception as e:
        return f"❌ Error creating file '{path}': {e}"


@tool
def read_file(path: str, start_line: int = None, end_line: int = None) -> str:
    """
    Read and return the contents of a file.
    Supports optional chunk reading via start_line and end_line (1-indexed, inclusive).
    If neither is provided, the full file content is returned.

    Args:
        path: Relative path to the file within the project.
        start_line: Optional 1-indexed start line to read from (inclusive).
        end_line: Optional 1-indexed end line to read up to (inclusive).

    Returns:
        The file content (or requested chunk) as a string, or an error message.
    """
    try:
        target = resolve_path(path)
        content = target.read_text(encoding="utf-8")

        if start_line is not None or end_line is not None:
            lines = content.splitlines(keepends=True)
            total_lines = len(lines)

            # Default start_line to 1 and end_line to total_lines if not set
            sl = max(1, start_line if start_line is not None else 1)
            el = min(total_lines, end_line if end_line is not None else total_lines)

            if sl > total_lines:
                return f"❌ start_line ({sl}) exceeds total lines ({total_lines}) in '{path}'."
            if sl > el:
                return f"❌ start_line ({sl}) is greater than end_line ({el})."

            chunk = lines[sl - 1 : el]
            header = f"[Lines {sl}-{el} of {total_lines} in '{path}']\n"
            return header + "".join(chunk)

        return content
    except FileNotFoundError:
        return f"❌ File not found: '{path}' (resolved to {resolve_path(path)})"
    except Exception as e:
        return f"❌ Error reading file '{path}': {e}"


@tool
def list_directory(path: str = ".") -> str:
    """
    List all files and subdirectories inside the given directory (recursive).

    Args:
        path: Relative path to the directory (defaults to project root).

    Returns:
        A formatted tree-like string of the directory contents.
    """
    try:
        target = resolve_path(path)
        if not target.exists():
            return f"❌ Directory does not exist: '{path}' (resolved to {target})"
        if not target.is_dir():
            return f"❌ Path is not a directory: '{path}'"

        lines = []
        IGNORE_DIRS = {".git", ".venv", "__pycache__"}
        for item in sorted(target.rglob("*")):
            rel = item.relative_to(target)
            if any(part in IGNORE_DIRS for part in rel.parts):
                continue
            prefix = "  " * (len(rel.parts) - 1)
            icon = "📁" if item.is_dir() else "📄"
            lines.append(f"{prefix}{icon} {item.name}")

        return "\n".join(lines) if lines else "(empty directory)"
    except Exception as e:
        return f"❌ Error listing directory '{path}': {e}"


@tool
def create_directory(path: str) -> str:
    """
    Create a directory (and all parent directories) at the given path.

    Args:
        path: Relative path for the new directory within the project.

    Returns:
        A success/error message string.
    """
    try:
        target = resolve_path(path)
        target.mkdir(parents=True, exist_ok=True)
        return f"✅ Directory created: {target}"
    except Exception as e:
        return f"❌ Error creating directory '{path}': {e}"


@tool
def replace_multiple_contents(path: str, replacements: list[dict]) -> str:
    """
    Find and replace multiple strings in a single file in one operation.
    
    Args:
        path: Relative path to the file within the project.
        replacements: A list of dicts, each containing 'search' and 'replace' keys.
                      Example: [{"search": "old_text", "replace": "new_text"}, ...]
        
    Returns:
        Confirmation message detailing how many replacements were successful.
    """
    try:
        target = resolve_path(path)
        if not target.exists():
            return f"❌ Error: File '{path}' does not exist."
        
        content = target.read_text(encoding="utf-8")
        original_content = content
        success_count = 0
        missing_snippets = []

        for item in replacements:
            search_str = item.get("search")
            replace_str = item.get("replace")
            
            if search_str in content:
                # Replace the first occurrence of this specific snippet
                content = content.replace(search_str, replace_str, 1)
                success_count += 1
            else:
                missing_snippets.append(search_str)

        if missing_snippets:
            error_msg = f"⚠️ Partial success. Applied {success_count} updates, but could not find {len(missing_snippets)} snippets: "
            error_msg += ", ".join([f"'{s[:20]}...'" for s in missing_snippets])
            # Even with partial failure, we save what we successfully matched
            target.write_text(content, encoding="utf-8")
            return error_msg

        target.write_text(content, encoding="utf-8")
        return f"✅ Successfully applied all {success_count} replacements in '{path}'."

    except Exception as e:
        return f"❌ Error processing replacements in '{path}': {e}"


# Exported list of tools for the CodeGenerator agent
FILE_TOOLS = [create_file, read_file, list_directory, create_directory, replace_multiple_contents]
