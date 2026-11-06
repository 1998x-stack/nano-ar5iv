"""M05 golden-based quality gates and adversarial failure evidence."""
import copy
import json
import unittest
from dataclasses import replace
from nano_ar5iv.domain.documents import PaperDocument
from nano_ar5iv.normalization.xml_to_ir import normalize_latexml_xml
from nano_ar5iv.normalization.html_to_ir import normalize_latexml_html
from nano_ar5iv.quality.reporting import assess_document
from nano_ar5iv.quality.reference import parse_golden, InvalidGolden
from nano_ar5iv.quality.mathematical import mathml_tokens

SOURCE_XML = b'''<ltx:document xmlns:ltx="http://dlmf.nist.gov/LaTeXML"
 xmlns:m="http://www.w3.org/1998/Math/MathML">
 <ltx:section xml:id="s"><ltx:title>Introduction</ltx:title>
  <ltx:para><ltx:p>Independent test text
   <ltx:Math tex="a+b"><m:math><m:mi>a</m:mi><m:mo>+</m:mo><m:mi>b</m:mi></m:math></ltx:Math>
  </ltx:p></ltx:para></ltx:section>
 </ltx:document>'''

SOURCE_HTML = b'''<html><body><section class="ltx_section" id="s">
 <h2 class="ltx_title">Introduction</h2>
 <p class="ltx_p">Independent test text
 <math><mi>a</mi><mo>+</mo><mi>b</mi></math></p>
 </section></body></html>'''


def golden_data():
    return {
        "schema_version": "1.0", "source_bundle_id": "a"*64, "root_path": "paper.tex",
        "review": {"reviewer": "test fixture author", "evidence_method": "independently authored minimal TeX"},
        "expected": {
            "sections": ["Introduction"], "paragraphs_contain": ["Independent test text"],
            "equations": [{"tex": "a+b", "mathml_tokens": ["a", "+", "b"]}],
            "citations": [], "bibliography": [], "figures": [], "tables": [],
            "visual": "NOT_APPLICABLE"
        }
    }


def reference(data=None):
    return parse_golden(json.dumps(golden_data() if data is None else data, sort_keys=True).encode())


def source_document():
    return normalize_latexml_xml(
        SOURCE_XML, bundle_id="a"*64, root_path="paper.tex",
        provenance={"source_bundle_id": "a"*64, "run_id": "b"*32},
        engine={"name": "LaTeXML", "status": "SUCCEEDED", "exit_code": 0})


def assess(document=None, expected=None):
    return assess_document(document or source_document(), "e"*64, "d"*64,
                           reference(expected) if expected is not False else None, {})


class M05GateTests(unittest.TestCase):
    def test_all_independent_fixture_assertions_can_pass(self):
        result = assess()
        self.assertEqual(result.decision, "ACCEPTED")
        self.assertEqual(result.dimensions["visual"].status, "NOT_APPLICABLE")
        self.assertEqual(result.dimensions["mathematics"].status, "PASS")
        self.assertEqual(result.dimensions["provenance"].status, "PASS")
        self.assertFalse(result.provenance["reference_identity_independently_authenticated"])
        self.assertIn("supplied golden", result.provenance["scope"])

    def test_no_golden_cannot_be_accepted_even_when_engine_succeeded(self):
        result = assess(expected=False)
        self.assertEqual(result.decision, "REVIEW_REQUIRED")
        self.assertEqual(result.dimensions["mathematics"].status, "UNKNOWN")
        self.assertEqual(result.dimensions["visual"].status, "NOT_RUN")
        self.assertIn("MATH_NO_GOLDEN", result.reason_codes)

    def test_math_symbol_corruption_rejected_without_fatal_engine(self):
        doc = source_document()
        doc.equations = [replace(doc.equations[0], presentation_mathml="<math><mi>x</mi></math>")]
        result = assess(doc)
        self.assertEqual(result.decision, "REJECTED")
        self.assertIn("MATH_SYMBOL_MISMATCH", result.reason_codes)

    def test_tex_string_mismatch_is_hard_failure(self):
        doc = source_document()
        doc.equations = [replace(doc.equations[0], source_tex="a-b")]
        self.assertIn("EQUATION_TEX_MISMATCH", assess(doc).reason_codes)

    def test_mathml_missing_or_invalid_is_hard_failure(self):
        doc = source_document()
        doc.equations = [replace(doc.equations[0], presentation_mathml=None)]
        self.assertIn("MATHML_UNUSABLE", assess(doc, expected=False).reason_codes)
        doc.equations = [replace(doc.equations[0], presentation_mathml="<!DOCTYPE math><math/>")]
        self.assertEqual(assess(doc).decision, "REJECTED")

    def test_missing_equation_is_rejected_not_assumed_absent_in_original(self):
        doc = source_document()
        doc.equations = []
        result = assess(doc)
        self.assertIn("EQUATION_COUNT_MISMATCH", result.reason_codes)
        self.assertEqual(result.decision, "REJECTED")

    def test_unresolved_citation_rejected(self):
        xml = SOURCE_XML.replace(b"</ltx:p>", b'<ltx:ref idref="missing">[?]</ltx:ref></ltx:p>')
        doc = normalize_latexml_xml(xml, bundle_id="a"*64, root_path="paper.tex",
            provenance={"source_bundle_id": "a"*64}, engine={"status": "SUCCEEDED", "exit_code": 0})
        result = assess(doc, expected=False)
        self.assertEqual(result.decision, "REJECTED")
        self.assertIn("UNRESOLVED_SCIENTIFIC_REFERENCE", result.reason_codes)

    def test_duplicate_id_and_invalid_parent_rejected(self):
        doc = source_document()
        doc.equations = [replace(doc.equations[0], id=doc.nodes[0].id)]
        self.assertIn("DUPLICATE_IR_ID", assess(doc).reason_codes)
        doc = source_document()
        doc.nodes = [replace(doc.nodes[0], parent_id="missing")] + doc.nodes[1:]
        self.assertIn("ORPHAN_PARENT", assess(doc).reason_codes)

    def test_bad_section_and_missing_paragraph_rejected(self):
        data = golden_data()
        data["expected"]["sections"] = ["Wrong title"]
        self.assertIn("SECTION_MISMATCH", assess(expected=data).reason_codes)
        data = golden_data()
        data["expected"]["paragraphs_contain"] = ["Not in document"]
        self.assertIn("MISSING_PARAGRAPH_TEXT", assess(expected=data).reason_codes)

    def test_wrong_source_bound_golden_rejected(self):
        data = golden_data()
        data["source_bundle_id"] = "c"*64
        result = assess(expected=data)
        self.assertEqual(result.decision, "REJECTED")
        self.assertIn("GOLDEN_SOURCE_MISMATCH", result.reason_codes)

    def test_html_fallback_never_auto_accepted_even_if_tokens_match(self):
        doc = normalize_latexml_html(
            SOURCE_HTML, bundle_id="a"*64, root_path="paper.tex",
            provenance={"source_bundle_id": "a"*64},
            engine={"status": "SUCCEEDED", "exit_code": 0})
        data = golden_data()
        data["expected"]["equations"] = [{"mathml_tokens": ["a","+","b"]}]
        result = assess(doc, expected=data)
        self.assertNotEqual(result.decision, "ACCEPTED")
        self.assertEqual(result.dimensions["provenance"].status, "UNKNOWN")
        self.assertIn("HTML_OR_UNKNOWN_PROVENANCE", result.reason_codes)

    def test_unknown_theorem_blocks_acceptance(self):
        doc = source_document()
        from nano_ar5iv.domain.documents import UnknownNode
        doc.unknown_nodes = [UnknownNode("t1", "theorem", "s", "<theorem>x</theorem>")]
        result = assess(doc)
        self.assertNotEqual(result.decision, "ACCEPTED")
        self.assertEqual(result.dimensions["provenance"].status, "UNKNOWN")

    def test_no_unverified_visual_may_be_accepted(self):
        data = golden_data()
        data["expected"]["visual"] = "REQUIRED"
        result = assess(expected=data)
        self.assertEqual(result.decision, "REVIEW_REQUIRED")
        self.assertEqual(result.dimensions["visual"].status, "NOT_RUN")

    def test_table_cell_modification_rejected(self):
        xml = SOURCE_XML.replace(b"</ltx:section>", b'<ltx:table><ltx:tr><ltx:td>7</ltx:td></ltx:tr></ltx:table></ltx:section>')
        doc = normalize_latexml_xml(
            xml, bundle_id="a"*64, root_path="paper.tex",
            provenance={"source_bundle_id": "a"*64},
            engine={"status": "SUCCEEDED", "exit_code": 0})
        data = golden_data()
        data["expected"]["tables"] = [{"rows": [[{"text":"8","rowspan":1,"colspan":1}]]}]
        data["expected"]["visual"] = "REQUIRED"
        result = assess(doc, expected=data)
        self.assertEqual(result.decision, "REJECTED")
        self.assertIn("TABLE_CELL_MISMATCH", result.reason_codes)

    def test_unsafe_figure_rejected(self):
        from nano_ar5iv.domain.documents import Asset
        doc = source_document()
        doc.assets.append(Asset("f1","figure","../private.png",availability="UNSAFE_PATH"))
        result = assess(doc, expected=False)
        self.assertEqual(result.decision, "REJECTED")
        self.assertIn("UNSAFE_ASSET_URI", result.reason_codes)

    def test_inline_svg_without_file_uri_is_unknown_not_unsafe(self):
        from nano_ar5iv.domain.documents import Asset
        doc = source_document()
        doc.assets.append(Asset("inline-svg", "image", None, availability="MISSING_REFERENCE"))
        result = assess(doc, expected=False)
        self.assertNotEqual(result.decision, "REJECTED")
        self.assertEqual(result.dimensions["assets"].status, "UNKNOWN")
        self.assertIn("INLINE_OR_UNMAPPED_FIGURE", result.reason_codes)

    def test_unsupported_golden_fields_and_no_review_provenance(self):
        data = golden_data()
        del data["expected"]["sections"]
        with self.assertRaises(InvalidGolden):
            reference(data)
        data = golden_data()
        data["review"] = {}
        with self.assertRaises(InvalidGolden):
            reference(data)
        data = golden_data()
        data["expected"]["visual"] = {"oops": True}
        with self.assertRaises(InvalidGolden):
            reference(data)

    def test_mathml_token_parser_blocks_entities(self):
        self.assertEqual(mathml_tokens("<math><mi>x</mi><mo>+</mo><mn>2</mn></math>"),
                         ("x", "+", "2"))
        with self.assertRaises(ValueError):
            mathml_tokens('<!DOCTYPE math [<!ENTITY x "unsafe">]><math>&x;</math>')


if __name__ == "__main__":
    unittest.main()
