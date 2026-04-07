"""
test_tools.py – Code execution and testing tools for the Tester agent.

These tools allow the agent to run Python code, execute pytest,
and inspect generated files.
"""

import subprocess
import sys
import textwrap
from pathlib import Path
from langchain_core.tools import tool


@tool
def run_python_code(code: str) -> str:
    """
    Execute a Python code snippet in a subprocess and return its output.

    Use this to quickly validate logic, run small test cases, or
    verify that generated code is importable and functional.

    Args:
        code: Valid Python code to execute.

    Returns:
        Combined stdout + stderr output, or error details.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-c", textwrap.dedent(code)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = ""
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}"
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        output += f"\nReturn code: {result.returncode}"
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "❌ Execution timed out (30s limit)"
    except Exception as e:
        return f"❌ Error running code: {e}"


@tool
def run_pytest(directory: str, extra_args: str = "") -> str:
    """
    Run pytest on the specified directory or file and return the output.

    Args:
        directory: Path to the directory or file to run pytest on.
        extra_args: Optional extra pytest arguments (e.g. '-v', '-k test_name').

    Returns:
        Full pytest output including pass/fail summary.
    """
    try:
        target = Path(directory)
        if not target.exists():
            return f"❌ Path does not exist: '{directory}'"

        cmd = [sys.executable, "-m", "pytest", str(target), "--tb=short", "-v"]
        if extra_args:
            cmd.extend(extra_args.split())

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = (result.stdout or "") + (result.stderr or "")
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "❌ pytest timed out (120s limit)"
    except Exception as e:
        return f"❌ Error running pytest: {e}"


@tool
def read_file(path: str) -> str:
    """
    Read and return the contents of a generated file for inspection.

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
        A formatted list of the directory contents.
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


# Exported list of tools for the Tester agent
TEST_TOOLS = [run_python_code, run_pytest, read_file, list_directory]
