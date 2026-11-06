"""Resolve static TeX includes without following paths outside the snapshot."""
from __future__ import annotations
from pathlib import PurePosixPath


def dependency_graph(scans: dict[str, dict], available: set[str]) -> dict:
    edges: list[dict] = []
    diagnostics: list[str] = []
    referenced_by: dict[str, list[str]] = {name: [] for name in scans}
    for source, scan in scans.items():
        for dep in scan["dependencies"]:
            name = dep["target"]
            candidate = PurePosixPath(name)
            if candidate.is_absolute() or "\\" in name or any(p in {"..", ".", ""} for p in name.split("/")):
                diagnostics.append("unsafe_dependency:" + source + ":" + name)
                continue
            choices = []
            for base in (PurePosixPath(), PurePosixPath(source).parent):
                p = base / candidate
                for probe in ([p] if p.suffix else [p.with_suffix(".tex"), p.with_suffix(".ltx")]):
                    value = str(probe)
                    if value in available and value not in choices:
                        choices.append(value)
            if len(choices) == 1:
                target = choices[0]
                edges.append({"source": source, "target": target, "command": dep["command"]})
                if target in referenced_by and source not in referenced_by[target]:
                    referenced_by[target].append(source)
            elif len(choices) > 1:
                diagnostics.append("ambiguous_dependency:" + source + ":" + name)
            else:
                diagnostics.append("missing_dependency:" + source + ":" + name)
    neighbors: dict[str, list[str]] = {p: [] for p in scans}
    for edge in edges:
        if edge["target"] in neighbors:
            neighbors[edge["source"]].append(edge["target"])
    visited: set[str] = set()
    visiting: set[str] = set()
    def walk(node: str) -> None:
        if node in visiting:
            diagnostics.append("dependency_cycle:" + node)
            return
        if node in visited:
            return
        visiting.add(node)
        for child in neighbors[node]:
            walk(child)
        visiting.remove(node)
        visited.add(node)
    for root in sorted(neighbors):
        walk(root)
    return {"edges": edges, "referenced_by": {k: sorted(v) for k, v in referenced_by.items()},
            "diagnostics": sorted(set(diagnostics))}
