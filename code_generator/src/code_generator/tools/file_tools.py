"""
file_tools.py – File system tools for the CodeGenerator agent.

These tools allow the agent to create directories and files,
read existing files, and list directory contents.
"""

import os
from pathlib import Path
from langchain_core.tools import tool


@tool
def create_file(path: str, content: str) -> str:
    """
    Create or overwrite a file at the given path with the provided content.
    Parent directories are created automatically if they don't exist.

    Args:
        path: Absolute or relative path to the file to create.
        content: The full content to write into the file.

    Returns:
        A success/error message string.
    """
    try:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"✅ File created: {target.resolve()} ({len(content)} chars)"
    except Exception as e:
        return f"❌ Error creating file '{path}': {e}"


@tool
def read_file(path: str) -> str:
    """
    Read and return the contents of a file.

    Args:
        path: Absolute or relative path to the file.

    Returns:
        The file content as a string, or an error message.
    """
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"❌ File not found: '{path}'"
    except Exception as e:
        return f"❌ Error reading file '{path}': {e}"


@tool
def list_directory(path: str) -> str:
    """
    List all files and subdirectories inside the given directory (recursive).

    Args:
        path: Absolute or relative path to the directory.

    Returns:
        A formatted tree-like string of the directory contents.
    """
    try:
        target = Path(path)
        if not target.exists():
            return f"❌ Directory does not exist: '{path}'"
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
        path: Absolute or relative path for the new directory.

    Returns:
        A success/error message string.
    """
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return f"✅ Directory created: {Path(path).resolve()}"
    except Exception as e:
        return f"❌ Error creating directory '{path}': {e}"


# Exported list of tools for the CodeGenerator agent
FILE_TOOLS = [create_file, read_file, list_directory, create_directory]
