from __future__ import annotations
import json
from pathlib import Path

from code_base_understander.models import FileNode, ProjectSkeleton


def save_skeleton(skeleton: ProjectSkeleton, path: str) -> None:
    data = {
        "root": skeleton.root,
        "tech_stack": skeleton.tech_stack,
        "entry_points": skeleton.entry_points,
        "route_manifest": skeleton.route_manifest,
        "import_graph": skeleton.import_graph,
        "files": {
            rel: {
                "path": node.path,
                "role": node.role,
                "symbols": node.symbols,
                "imports": node.imports,
                "exports": node.exports,
                "size_lines": node.size_lines,
            }
            for rel, node in skeleton.files.items()
        },
    }
    Path(path).write_text(json.dumps(data, indent=2))


def load_skeleton(path: str) -> ProjectSkeleton:
    data = json.loads(Path(path).read_text())
    files = {
        rel: FileNode(**node_data)
        for rel, node_data in data["files"].items()
    }
    return ProjectSkeleton(
        root=data["root"],
        tech_stack=data["tech_stack"],
        entry_points=data["entry_points"],
        route_manifest=data["route_manifest"],
        files=files,
        import_graph=data["import_graph"],
    )