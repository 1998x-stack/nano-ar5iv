"""M04 tolerant HTML5 reconstruction for ar5ivist output (no JS/network).

HTML is a lossy fallback relative to native LaTeXML XML; the result explicitly
marks unavailable source TeX and source spans as unknown.
"""
from __future__ import annotations
from html.parser import HTMLParser
import xml.etree.ElementTree as ET
from nano_ar5iv.normalization.xml_to_ir import (
    MAX_INPUT_BYTES, MAX_ELEMENTS, MAX_DEPTH, InvalidScientificMarkup,
    normalize_element_tree,
)

_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
         "meta", "param", "source", "track", "wbr"}


class _BoundedHTMLTree(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = ET.Element("html_document")
        self.stack = [self.root]
        self.count = 0
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        self.count += 1
        if self.count > MAX_ELEMENTS or len(self.stack) > MAX_DEPTH:
            raise InvalidScientificMarkup("HTML element/depth budget exceeded")
        tag = tag.lower()
        if tag in {"script", "style"}:
            self.skip += 1
            return
        if self.skip:
            return
        parent = self.stack[-1]
        el = ET.SubElement(parent, tag)
        for k, v in attrs:
            if k and v is not None and len(k) < 256 and len(v) < 4096:
                el.set(k, v)
        if tag not in _VOID:
            self.stack.append(el)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag.lower() not in _VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in {"script", "style"} and self.skip:
            self.skip -= 1
            return
        if self.skip:
            return
        for i in range(len(self.stack)-1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if self.skip or not data:
            return
        if len(data) > MAX_INPUT_BYTES:
            raise InvalidScientificMarkup("Oversize HTML text node")
        current = self.stack[-1]
        if len(current):
            last = current[-1]
            last.tail = (last.tail or "") + data
        else:
            current.text = (current.text or "") + data


def normalize_latexml_html(data: bytes, *, bundle_id: str, root_path: str,
                           provenance: dict, engine: dict):
    if len(data) > MAX_INPUT_BYTES or not data.strip():
        raise InvalidScientificMarkup("HTML empty or larger than parsing budget")
    html = _BoundedHTMLTree()
    try:
        html.feed(data.decode("utf-8", "replace"))
        html.close()
    except (ValueError, OverflowError) as exc:
        raise InvalidScientificMarkup("Malformed/budget-exceeded HTML") from exc
    return normalize_element_tree(html.root, bundle_id=bundle_id, root_path=root_path,
                                  provenance=provenance, engine=engine, input_format="html")
