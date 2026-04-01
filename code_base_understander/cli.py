from __future__ import annotations
import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from .indexer import ProjectIndexer
from .query import ContextQuery
from .storage import load_skeleton, save_skeleton

from dotenv import load_dotenv
load_dotenv()

console = Console()

DEFAULT_SKELETON_FILE = ".ctx_skeleton.json"


@click.group()
def cli():
    """Codebase context understanding system."""


@cli.command()
@click.argument("project_dir", default=".")
@click.option("--output", "-o", default=None, help="Where to save skeleton JSON (default: <project>/.ctx_skeleton.json)")
def index(project_dir: str, output: str | None):
    """
    Index a project and build its skeleton map.

    Run this once per project (or after major structural changes).
    """
    root = Path(project_dir).resolve()
    if not root.exists():
        console.print(f"[red]Directory not found: {root}[/red]")
        sys.exit(1)

    output_path = output or str(root / DEFAULT_SKELETON_FILE)

    console.print(f"[bold]Indexing project:[/bold] {root}")

    indexer = ProjectIndexer(str(root))
    skeleton = indexer.index()

    save_skeleton(skeleton, output_path)

    # Print summary table
    table = Table(title="Project Skeleton", show_header=True)
    table.add_column("Attribute", style="cyan")
    table.add_column("Value")

    table.add_row("Tech Stack", ", ".join(skeleton.tech_stack))
    table.add_row("Total Files Indexed", str(len(skeleton.files)))
    table.add_row("Entry Points", ", ".join(skeleton.entry_points) or "none")
    table.add_row("Routes Found", str(len(skeleton.route_manifest)))
    table.add_row("Skeleton Saved To", output_path)

    console.print(table)

    # Role breakdown
    from collections import Counter
    roles = Counter(n.role for n in skeleton.files.values())
    role_table = Table(title="File Roles", show_header=True)
    role_table.add_column("Role", style="green")
    role_table.add_column("Count")
    for role, count in roles.most_common():
        role_table.add_row(role, str(count))
    console.print(role_table)


@cli.command()
@click.argument("query")
@click.option("--project", "-p", default=".", help="Project directory (must be indexed already)")
@click.option("--skeleton", "-s", default=None, help="Path to skeleton JSON (default: <project>/.ctx_skeleton.json)")
@click.option("--show-content", is_flag=True, default=False, help="Print full file contents")
def ask(query: str, project: str, skeleton: str | None, show_content: bool):
    """
    Query a project for relevant files.

    Example:
        ctx ask "add a cart page" --project ./my-ecommerce
    """
    root = Path(project).resolve()
    skeleton_path = skeleton or str(root / DEFAULT_SKELETON_FILE)

    if not Path(skeleton_path).exists():
        console.print(f"[red]No skeleton found at {skeleton_path}. Run 'ctx index {project}' first.[/red]")
        sys.exit(1)

    if not os.environ.get("GROQ_API_KEY"):
        console.print("[red]GROQ_API_KEY environment variable not set.[/red]")
        sys.exit(1)

    console.print(f"[bold]Query:[/bold] {query}")
    console.print(f"[dim]Loading skeleton from {skeleton_path}...[/dim]")

    sk = load_skeleton(skeleton_path)
    cq = ContextQuery(sk)

    with console.status("[bold green]Finding relevant files..."):
        result = cq.query(query)

    console.print(Panel(result.summary, title="Summary", border_style="green"))

    for fc in result.files:
        header = f"[bold]{fc.path}[/bold]  [dim]{fc.role}[/dim]\n[italic]{fc.why_relevant}[/italic]"
        console.print(Panel(header, border_style="blue"))

        if show_content:
            ext = Path(fc.path).suffix.lstrip(".")
            lang = {"ts": "typescript", "tsx": "typescript", "js": "javascript",
                    "jsx": "javascript", "py": "python"}.get(ext, "text")
            console.print(Syntax(fc.content, lang, line_numbers=True, theme="monokai"))


@cli.command()
@click.argument("project_dir", default=".")
@click.option("--skeleton", "-s", default=None)
def info(project_dir: str, skeleton: str | None):
    """Show what's in a project skeleton without running a query."""
    root = Path(project_dir).resolve()
    skeleton_path = skeleton or str(root / DEFAULT_SKELETON_FILE)

    if not Path(skeleton_path).exists():
        console.print(f"[red]No skeleton at {skeleton_path}[/red]")
        sys.exit(1)

    sk = load_skeleton(skeleton_path)

    console.print(f"[bold]Root:[/bold] {sk.root}")
    console.print(f"[bold]Stack:[/bold] {', '.join(sk.tech_stack)}")
    console.print(f"[bold]Files:[/bold] {len(sk.files)}")

    if sk.route_manifest:
        console.print("\n[bold]Routes:[/bold]")
        for route, path in sk.route_manifest.items():
            console.print(f"  {route} → {path}")