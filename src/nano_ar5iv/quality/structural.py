"""M05 structure invariants plus externally supplied section/text assertions."""
from __future__ import annotations
from nano_ar5iv.domain.documents import PaperDocument
from nano_ar5iv.ports.quality import Dimension, Finding
from nano_ar5iv.quality.reference import Golden

_SECTION_KINDS = frozenset({"part","chapter","section","subsection","subsubsection","abstract","subparagraph"})


def evaluate_structure(document: PaperDocument, reference: Golden | None) -> Dimension:
    problems: list[Finding] = []
    all_ids = [x.id for group in (document.nodes, document.equations, document.assets,
                                  document.citations, document.unknown_nodes) for x in group]
    if len(all_ids) != len(set(all_ids)):
        problems.append(Finding("DUPLICATE_IR_ID", "Canonical object IDs are not unique"))
    nodes = {node.id: node for node in document.nodes}
    for node in document.nodes:
        if node.parent_id and node.parent_id not in nodes:
            problems.append(Finding("ORPHAN_PARENT", "Parent node not present", node.id, node.parent_id))
        for child in node.children:
            if child not in nodes or nodes[child].parent_id != node.id:
                problems.append(Finding("INVALID_CHILD_EDGE", "Child/parent linkage inconsistent", node.id, child))
    for node in document.nodes:
        current, visited = node, set()
        while current.parent_id:
            if current.id in visited:
                problems.append(Finding("STRUCTURAL_CYCLE", "Cycle detected", node.id))
                break
            visited.add(current.id)
            if current.parent_id not in nodes:
                break
            current = nodes[current.parent_id]
    if not (document.nodes or document.equations or document.assets):
        problems.append(Finding("EMPTY_SCIENTIFIC_IR", "No recognized scientific content"))
    if document.schema_version != "1.0":
        problems.append(Finding("UNKNOWN_IR_SCHEMA", "Unsupported IR schema", observed=document.schema_version))
    if reference is not None:
        actual_sections = [n.title for n in document.nodes
                           if n.kind in _SECTION_KINDS and n.title]
        if actual_sections != reference.expected["sections"]:
            problems.append(Finding("SECTION_MISMATCH", "Section titles/order differ from golden",
                                    observed=repr(actual_sections)[:300]))
        combined = "\n".join(n.text or "" for n in document.nodes if n.kind == "paragraph_text")
        for expected_text in reference.expected["paragraphs_contain"]:
            if expected_text not in combined:
                problems.append(Finding("MISSING_PARAGRAPH_TEXT",
                                        "Golden passage absent from normalized paragraphs",
                                        observed=expected_text[:160]))
    if problems:
        return Dimension("FAIL", tuple(problems), len(all_ids))
    if reference is None:
        return Dimension("UNKNOWN", (Finding("STRUCTURE_NO_GOLDEN",
                                            "IR internally consistent; source completeness not established"),),
                         len(all_ids))
    return Dimension("PASS", checked=len(all_ids))
