"""M04 LaTeXML XML -> canonical PaperDocument; no scientific quality claims."""
from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from dataclasses import replace
from typing import Any
from nano_ar5iv.domain.documents import (
    Asset, Citation, DocumentNode, Equation, PaperDocument, UnknownNode,
)
from nano_ar5iv.normalization.assets import classify_asset_href
from nano_ar5iv.normalization.citation_graph import build_relations

LTX_NS = "http://dlmf.nist.gov/LaTeXML"
MATH_NS = "http://www.w3.org/1998/Math/MathML"
XML_NS = "http://www.w3.org/XML/1998/namespace"
MAX_INPUT_BYTES = 20 * 1024 * 1024
MAX_ELEMENTS = 25000
MAX_DEPTH = 128
_STRUCTURAL = {"part", "chapter", "section", "subsection", "subsubsection",
               "paragraph", "subparagraph", "abstract", "p", "equation",
               "equationgroup", "bibitem", "bibentry"}
_SECTIONS = {"part", "chapter", "section", "subsection", "subsubsection",
             "paragraph", "subparagraph", "abstract"}
_UNKNOWN_STRUCTURAL = {"theorem", "proof", "listing", "algorithm", "slide", "sidebar",
                       "verbatim", "glossary", "index", "acknowledgements"}
_KNOWN = _STRUCTURAL | {
    "document", "title", "subtitle", "para", "Math", "XMath", "XMTok", "XMApp",
    "XMArg", "XMRow", "XMDual", "XMWrap", "XMText", "XMRef", "XMath", "MathFork",
    "MathBranch", "figure", "float", "graphics", "picture", "caption",
    "table", "tabular", "tr", "td", "thead", "tbody", "cite", "bibref",
    "ref", "text", "emph", "break", "tag", "biblist", "bibliography", "bib-data",
    "bib-key", "bib-title", "bib-name", "bib-date", "bibentry", "bibitem",
    "anchor", "note", "itemize", "enumerate", "item", "description",
    "quote", "inline-item", "inline-block", "block", "tags",
}


class InvalidScientificMarkup(ValueError):
    """Rejected unsafe, out-of-budget or malformed structural markup."""


def localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":", 1)[-1]


def _text(el: ET.Element) -> str:
    return " ".join("".join(el.itertext()).split())


def _source_id(el: ET.Element) -> str | None:
    return el.get("{" + XML_NS + "}id") or el.get("id")


def _title(el: ET.Element) -> str | None:
    for child in el:
        if localname(child.tag) == "title":
            value = _text(child)
            return value or None
    return None


def _markup(el: ET.Element, cap: int = 4096) -> tuple[str, bool]:
    raw = ET.tostring(el, encoding="unicode")
    return raw[:cap], len(raw) > cap


def _math_tex(el: ET.Element) -> str | None:
    explicit = el.get("tex") or el.get("data-tex")
    if explicit:
        return explicit
    for child in el.iter():
        if localname(child.tag) == "annotation" and "tex" in (child.get("encoding") or "").lower():
            val = "".join(child.itertext()).strip()
            if val:
                return val
    return None


def _mathml(el: ET.Element) -> str | None:
    if localname(el.tag).lower() == "math":
        return ET.tostring(el, encoding="unicode")
    for child in el.iter():
        if localname(child.tag).lower() == "math":
            return ET.tostring(child, encoding="unicode")
    return None


def _classed(el: ET.Element, token: str) -> bool:
    return token in (el.get("class") or "").split()


def _is_section(el: ET.Element, fmt: str) -> str | None:
    name = localname(el.tag)
    if fmt == "xml":
        return name if name in _SECTIONS else None
    for kind in _SECTIONS:
        if _classed(el, "ltx_" + kind):
            return kind
    return name if name in {"section", "article"} and _classed(el, "ltx_section") else None


def _is_node(el: ET.Element, fmt: str) -> str | None:
    name = localname(el.tag).lower()
    section = _is_section(el, fmt)
    if section:
        return section
    if fmt == "xml":
        if name == "p":
            return "paragraph_text"
        if name in {"equation", "equationgroup", "bibitem", "bibentry"}:
            return "bibliography_item" if name in {"bibitem", "bibentry"} else name
        return None
    classes = set((el.get("class") or "").split())
    if name == "p" and ("ltx_p" in classes or any(c.startswith("ltx_") for c in classes)):
        return "paragraph_text"
    if name == "p" and not classes:
        return "paragraph_text"
    if "ltx_equation" in classes:
        return "equation"
    if "ltx_equationgroup" in classes:
        return "equationgroup"
    if "ltx_bibitem" in classes or "ltx_bibentry" in classes:
        return "bibliography_item"
    return None


def _is_figure(el: ET.Element, fmt: str) -> bool:
    if fmt == "xml":
        return localname(el.tag) in {"figure", "float"}
    return localname(el.tag).lower() == "figure" or _classed(el, "ltx_figure")


def _is_table(el: ET.Element, fmt: str) -> bool:
    if fmt == "xml":
        return localname(el.tag) == "table"
    return _classed(el, "ltx_table") or (localname(el.tag).lower() == "table" and
           not _classed(el, "ltx_tabular"))


def _is_image(el: ET.Element, fmt: str) -> bool:
    return localname(el.tag).lower() in ({"graphics", "picture"} if fmt == "xml" else {"img", "svg"})


def _is_citation(el: ET.Element, fmt: str, inside_cite: bool) -> str | None:
    name = localname(el.tag).lower()
    if fmt == "xml":
        if name == "bibref":
            return "citation"
        if name == "cite" and not any(localname(x.tag) == "bibref" for x in el.iter() if x is not el):
            return "citation"
        if name == "ref":
            return "reference"
    elif name == "a" and (_classed(el, "ltx_ref") or _classed(el, "ltx_cite")):
        return "citation" if inside_cite or _classed(el, "ltx_cite") else "reference"
    return None


def _target(el: ET.Element) -> str | None:
    return el.get("idref") or el.get("href") or el.get("key") or el.get("target")


def _asset_href(el: ET.Element) -> str | None:
    for child in el.iter():
        if localname(child.tag).lower() in {"graphics", "picture", "img", "svg"}:
            return child.get("src") or child.get("href") or child.get("file")
    return el.get("src") or el.get("href") or el.get("file")


def _caption(el: ET.Element) -> str | None:
    for child in el.iter():
        if localname(child.tag).lower() == "caption" or _classed(child, "ltx_caption"):
            return _text(child) or None
    return None


def _identifier(seed: str, kind: str, position: tuple[int, ...], original: str | None) -> str:
    location = "/".join(map(str, position))
    raw = f"{seed}|{kind}|{location}|{original or ''}"
    return kind[:3] + "_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def normalize_element_tree(root: ET.Element, *, bundle_id: str, root_path: str,
                           provenance: dict[str, Any], engine: dict[str, Any],
                           input_format: str) -> PaperDocument:
    if input_format not in {"xml", "html"}:
        raise InvalidScientificMarkup("input_format must be xml or html")
    document = PaperDocument(
        document_id="paper:" + hashlib.sha256((bundle_id + "|" + root_path).encode()).hexdigest()[:24],
        root_path=root_path, source_kind="latex_" + input_format,
        engine=dict(engine), provenance=dict(provenance))
    document.provenance["input_format"] = input_format
    if input_format == "html":
        document.warnings.append("HTML_DOM_RECONSTRUCTED: original LaTeXML XML/source spans unavailable")
    id_index: dict[str, str] = {}
    parent_children: dict[str, list[str]] = {}
    count = 0
    seed = document.document_id
    seen_ids: set[str] = set()

    def walk(el: ET.Element, path: tuple[int, ...], current_parent: str | None,
             figure_context: bool, math_context: bool, cite_context: bool,
             depth: int) -> None:
        nonlocal count
        count += 1
        if count > MAX_ELEMENTS or depth > MAX_DEPTH:
            raise InvalidScientificMarkup("Markup element/depth budget exceeded")
        if not isinstance(el.tag, str):
            return
        name = localname(el.tag)
        raw_id = _source_id(el)
        owner = current_parent
        node_kind = _is_node(el, input_format)
        if node_kind:
            canonical = _identifier(seed, "node", path, raw_id)
            title = _title(el) if node_kind in _SECTIONS else None
            text = _text(el) if node_kind in {"paragraph_text", "bibliography_item"} else None
            document.nodes.append(DocumentNode(canonical, node_kind, current_parent,
                                               title=title, text=text, source_id=raw_id))
            if current_parent:
                parent_children.setdefault(current_parent, []).append(canonical)
            owner = canonical
            if raw_id and raw_id not in id_index:
                id_index[raw_id] = canonical
            seen_ids.add(canonical)

        figure = _is_figure(el, input_format)
        table = _is_table(el, input_format)
        image = _is_image(el, input_format)
        if figure or table or (image and not figure_context):
            kind = "figure" if figure else ("table" if table else "image")
            aid = _identifier(seed, "asset", path, raw_id)
            href = _asset_href(el) if kind != "table" else None
            availability = classify_asset_href(href) if kind != "table" else "NOT_APPLICABLE"
            document.assets.append(Asset(aid, kind, href, _caption(el), owner,
                                         raw_id, availability))
            if raw_id and raw_id not in id_index:
                id_index[raw_id] = aid
        is_math = name == "Math" if input_format == "xml" else name.lower() == "math"
        if is_math and not math_context:
            eid = _identifier(seed, "equation", path, raw_id)
            document.equations.append(Equation(eid, _math_tex(el), _mathml(el),
                                               owner, raw_id))
            if raw_id and raw_id not in id_index:
                id_index[raw_id] = eid
        kind = _is_citation(el, input_format, cite_context)
        if kind:
            cid = _identifier(seed, "citation", path, raw_id)
            document.citations.append(Citation(cid, kind, _target(el), _text(el),
                                               owner, raw_id))
        # Keep unrecognized scientific structures, with bounded raw content.
        html_classes = set((el.get("class") or "").split())
        unsupported = (input_format == "xml" and name in _UNKNOWN_STRUCTURAL) or (
            input_format == "html" and
            bool(html_classes & {"ltx_theorem", "ltx_proof", "ltx_listing",
                                 "ltx_algorithm", "ltx_verbatim"}))
        if unsupported:
            raw, truncated = _markup(el)
            document.unknown_nodes.append(UnknownNode(
                _identifier(seed, "unknown", path, raw_id), name, raw_id, raw, truncated))
            if truncated:
                document.warnings.append("UNKNOWN_MARKUP_TRUNCATED")
        next_figure = figure_context or figure
        next_math = math_context or is_math
        next_cite = cite_context or name.lower() == "cite" or _classed(el, "ltx_cite")
        for index, child in enumerate(el):
            walk(child, path + (index,), owner, next_figure, next_math, next_cite, depth + 1)

    walk(root, (), None, False, False, False, 0)
    document.nodes = [replace(n, children=tuple(parent_children.get(n.id, ())))
                      for n in document.nodes]
    document.relations = build_relations(document.citations, id_index)
    if not document.nodes and not document.equations and not document.assets:
        document.warnings.append("NO_RECOGNIZED_SCIENTIFIC_CONTENT")
    return document


def normalize_latexml_xml(data: bytes, *, bundle_id: str, root_path: str,
                          provenance: dict[str, Any], engine: dict[str, Any]) -> PaperDocument:
    if len(data) > MAX_INPUT_BYTES or not data.strip():
        raise InvalidScientificMarkup("XML empty or larger than parsing budget")
    if re.search(rb"<!\s*(DOCTYPE|ENTITY)\b", data, re.IGNORECASE):
        raise InvalidScientificMarkup("DTD and entity declarations are forbidden")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise InvalidScientificMarkup("Malformed XML input") from exc
    if localname(root.tag).lower() not in {"document", "article"}:
        raise InvalidScientificMarkup("Expected a LaTeXML document root")
    return normalize_element_tree(root, bundle_id=bundle_id, root_path=root_path,
                                  provenance=provenance, engine=engine, input_format="xml")
