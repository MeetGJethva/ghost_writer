from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal


FileRole = Literal[
    "entry_point", "route", "page", "component", "service",
    "model", "config", "util", "test", "style", "unknown"
]


@dataclass
class FileNode:
    path: str                          # relative path from project root
    role: FileRole
    symbols: list[str]                 # functions, classes, exports defined here
    imports: list[str]                 # relative paths this file imports from
    exports: list[str]                 # names exported (for JS/TS)
    size_lines: int


@dataclass
class ProjectSkeleton:
    root: str                          # absolute path to project root
    tech_stack: list[str]              # e.g. ["Next.js", "TypeScript", "Prisma"]
    entry_points: list[str]            # relative paths of top-level entries
    route_manifest: dict[str, str]     # route pattern → file path
    files: dict[str, FileNode]         # relative path → FileNode
    import_graph: dict[str, list[str]] # relative path → list of imported relative paths

    def get_node(self, rel_path: str) -> FileNode | None:
        return self.files.get(rel_path)

    def dependents_of(self, rel_path: str) -> list[str]:
        """Files that import the given file."""
        return [
            src for src, targets in self.import_graph.items()
            if rel_path in targets
        ]

    def dependencies_of(self, rel_path: str) -> list[str]:
        """Files that the given file imports."""
        return self.import_graph.get(rel_path, [])


@dataclass
class FileContext:
    path: str
    role: FileRole
    content: str
    why_relevant: str                  # explanation of why this file was selected


@dataclass
class QueryResult:
    query: str
    files: list[FileContext]
    summary: str                       # brief explanation of what was gathered and why