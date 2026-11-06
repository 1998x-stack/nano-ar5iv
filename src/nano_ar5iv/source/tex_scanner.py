"""Bounded static TeX command scanner; NEVER expands macros or executes input.

Masks % comments, common verbatim environments, and inline \\verb; unresolved
dynamic paths are preserved as unknown instead of inventing dependencies.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


_VERBATIM_ENV = re.compile(
    r"(?<!\\)\\begin\s*\{(verbatim\*?|Verbatim|lstlisting|minted|comment|filecontents\*?)\}",
    re.ASCII,
)
_COMMAND = re.compile(r"(?<!\\)\\([a-zA-Z@]+)", re.ASCII)
_BARE = re.compile(r"[^\s{}\\%]+")
_INPUT_KINDS = frozenset({"input", "include", "subfile", "import", "subimport",
                          "inputfrom", "includefrom", "subincludefrom"})
_ASSET_KINDS = frozenset({"includegraphics", "bibliography", "addbibresource",
                          "usepackage", "RequirePackage", "documentclass"})


@dataclass(frozen=True)
class TeXRef:
    kind: str
    value: str
    line: int
    dynamic: bool = False


@dataclass(frozen=True)
class TeXScan:
    has_class: bool
    has_begin: bool
    has_end: bool
    has_section: bool
    references: tuple[TeXRef, ...]


def _spaces(value: str) -> str:
    return "".join("\n" if ch == "\n" else " " for ch in value)


def _mask_opaque(text: str) -> str:
    text = list(text)
    original = "".join(text)
    # Only literal environmental delimiters; nested/catcode-changing TeX remains out of scope.
    for match in reversed(list(_VERBATIM_ENV.finditer(original))):
        marker = r"\end{" + match.group(1) + "}"
        last = original.find(marker, match.end())
        stop = len(original) if last < 0 else last + len(marker)
        for i in range(match.start(), stop):
            if text[i] != "\n":
                text[i] = " "
    flattened = "".join(text)
    result = list(flattened)
    for match in re.finditer(r"(?<!\\)\\verb\*?", flattened):
        at = match.end()
        if at >= len(flattened) or flattened[at].isspace():
            continue
        delim = flattened[at]
        close = flattened.find(delim, at + 1)
        stop = len(flattened) if close < 0 else close + 1
        for i in range(match.start(), stop):
            if result[i] != "\n":
                result[i] = " "
    return "".join(result)


def _remove_comments(text: str) -> str:
    chars = list(text)
    i = 0
    while i < len(chars):
        if chars[i] == "%":
            preceding = i - 1
            count = 0
            while preceding >= 0 and chars[preceding] == "\\":
                count += 1
                preceding -= 1
            if count % 2 == 0:
                j = i
                while j < len(chars) and chars[j] != "\n":
                    chars[j] = " "
                    j += 1
                i = j
                continue
        i += 1
    return "".join(chars)


def _group(text: str, start: int) -> tuple[str | None, int]:
    i = start
    while i < len(text) and text[i].isspace():
        i += 1
    if i >= len(text) or text[i] != "{":
        return None, i
    opening = i + 1
    level = 1
    i = opening
    while i < len(text):
        if text[i] == "{":
            level += 1
        elif text[i] == "}":
            level -= 1
            if level == 0:
                return text[opening:i].strip(), i + 1
        i += 1
    return None, i


def scan_tex(source: str) -> TeXScan:
    text = _remove_comments(_mask_opaque(source))
    references: list[TeXRef] = []
    has_class = has_begin = has_end = has_section = False
    for match in _COMMAND.finditer(text):
        name, pos = match.group(1), match.end()
        if name in {"section", "chapter", "subsection"}:
            has_section = True
        if name in {"documentclass", "documentstyle"}:
            has_class = True
        if name in {"begin", "end"}:
            value, _ = _group(text, pos)
            if value == "document" and name == "begin":
                has_begin = True
            if value == "document" and name == "end":
                has_end = True
        if name not in _INPUT_KINDS and name not in _ASSET_KINDS:
            continue
        i = pos
        while i < len(text) and text[i].isspace():
            i += 1
        if i < len(text) and text[i] == "[":
            stop = text.find("]", i + 1)
            if stop < 0:
                continue
            i = stop + 1
        value, stop = _group(text, i)
        if value is None and name == "input":
            bare = _BARE.match(text, i)
            if bare:
                value, stop = bare.group(0), bare.end()
        if value is None:
            continue
        if name in {"import", "subimport", "inputfrom", "includefrom", "subincludefrom"}:
            next_value, _ = _group(text, stop)
            if next_value is None:
                continue
            value = value.rstrip("/") + "/" + next_value
        values = value.split(",") if name in {"bibliography", "usepackage", "RequirePackage"} else [value]
        for item in values:
            item = item.strip()
            if item:
                references.append(TeXRef(
                    name, item, text.count("\n", 0, match.start()) + 1,
                    "\\" in item or "#" in item or "{" in item or "}" in item))
    return TeXScan(has_class, has_begin, has_end, has_section, tuple(references))
