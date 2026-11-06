"""Conservative TeX lexical scanner, not a complete TeX macro interpreter."""
from __future__ import annotations
import re


def _remove_literal_regions(text: str) -> str:
    # Strip verbatim-like environments and inline verb first, then comments.
    for env in ("verbatim", "verbatim*", "lstlisting", "minted", "comment"):
        start = re.escape(r"\begin{" + env + "}")
        end = re.escape(r"\end{" + env + "}")
        text = re.sub(start + r".*?" + end, " ", text, flags=re.DOTALL)
    text = re.sub(r"\\verb\*?([^\w\s]).*?\1", " ", text, flags=re.DOTALL)
    cleaned = []
    for line in text.splitlines(keepends=True):
        cut = len(line)
        for i, char in enumerate(line):
            if char == "%" and i - len(line[:i].rstrip("\\")) & 1 == 0:
                cut = i
                break
        cleaned.append(line[:cut] + ("\n" if line.endswith("\n") else ""))
    return "".join(cleaned)


def scan_tex(text: str) -> dict:
    cleaned = _remove_literal_regions(text)
    deps: list[dict] = []
    issues: list[str] = []
    token = re.compile(r"\\(input|include|subfile|import|subimport)\b")
    for found in token.finditer(cleaned):
        command = found.group(1)
        suffix = cleaned[found.end():]
        if command in {"import", "subimport"}:
            m = re.match(r"\s*\{([^{}]*)\}\s*\{([^{}]*)\}", suffix)
            arg = (m.group(1) + "/" + m.group(2)) if m else None
        else:
            m = re.match(r"\s*\{([^{}]*)\}", suffix)
            if m:
                arg = m.group(1)
            else:
                m = re.match(r"\s+([a-zA-Z0-9_./-]+)", suffix)
                arg = m.group(1) if m else None
        if not arg or any(ch in arg for ch in "\\#$~{}"):
            issues.append("unresolved_dynamic:" + command)
            continue
        deps.append({"command": command, "target": arg.strip()})
    if re.search(r"\\includeonly\b", cleaned):
        issues.append("includeonly_requires_review")
    return {"has_documentclass": bool(re.search(r"\\document(class|style)\b", cleaned)),
            "has_begin_document": bool(re.search(r"\\begin\s*\{document\}", cleaned)),
            "has_end_document": bool(re.search(r"\\end\s*\{document\}", cleaned)),
            "has_plain_tex_bye": bool(re.search(r"\\bye\b", cleaned)),
            "dependencies": deps, "diagnostics": sorted(set(issues))}
