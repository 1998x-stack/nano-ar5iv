"""M03 deterministic wrapper text, using only explicit user-selected fragments."""
from __future__ import annotations


def render_wrapper(fragments: tuple[str, ...], documentclass: str) -> str:
    # Never rewrite or infer any scientific content.
    return (
        "% nano-ar5iv generated wrapper; manual review required\n"
        "\\documentclass{" + documentclass + "}\n"
        "\\begin{document}\n"
        + "".join("\\input{" + path + "}\n" for path in fragments)
        + "\\end{document}\n"
    )
