"""M04 structural IR tests: source fidelity, MathML, references and safe parsing."""
import json
import unittest
from nano_ar5iv.domain.provenance import sha256_bytes
from nano_ar5iv.normalization.html_to_ir import normalize_latexml_html
from nano_ar5iv.normalization.xml_to_ir import InvalidScientificMarkup, normalize_latexml_xml
from nano_ar5iv.normalization.assets import classify_asset_href
from nano_ar5iv.normalization.citation_graph import normalized_target


XML = b'''<?xml version="1.0" encoding="utf-8"?>
<ltx:document xmlns:ltx="http://dlmf.nist.gov/LaTeXML"
              xmlns:m="http://www.w3.org/1998/Math/MathML"
              xmlns:xml="http://www.w3.org/XML/1998/namespace">
  <ltx:section xml:id="s1"><ltx:title>Introduction</ltx:title>
    <ltx:para><ltx:p xml:id="p1">Text <ltx:Math tex="E=mc^2">
      <m:math><m:mi>E</m:mi><m:mo>=</m:mo><m:mi>mc^2</m:mi></m:math>
    </ltx:Math> and <ltx:ref idref="eq1">Eq. 1</ltx:ref>.
    <ltx:cite><ltx:bibref idref="bib1">[1]</ltx:bibref></ltx:cite>
    </ltx:p></ltx:para>
    <ltx:equation xml:id="eq1"><ltx:Math tex="x+y"><m:math><m:mi>x</m:mi></m:math></ltx:Math></ltx:equation>
    <ltx:figure xml:id="fig1"><ltx:caption>A diagram</ltx:caption>
      <ltx:graphics src="images/diagram.png"/></ltx:figure>
    <ltx:table xml:id="tab1"><ltx:caption>Measurements</ltx:caption>
      <ltx:tabular><ltx:tr><ltx:td>7</ltx:td></ltx:tr></ltx:tabular></ltx:table>
    <ltx:theorem xml:id="thm1"><ltx:p>Nonstandard scientific structure.</ltx:p></ltx:theorem>
  </ltx:section>
  <ltx:bibliography><ltx:biblist><ltx:bibitem xml:id="bib1">Source A</ltx:bibitem></ltx:biblist></ltx:bibliography>
</ltx:document>'''

HTML = b'''<!doctype html><html><body><article class="ltx_document">
<section class="ltx_section" id="s1"><h2 class="ltx_title">Introduction</h2>
<div class="ltx_para"><p class="ltx_p">Text
<math xmlns="http://www.w3.org/1998/Math/MathML"><mi>x</mi><mo>=</mo><mn>1</mn></math>
<a class="ltx_ref ltx_cite" href="#bib1">[1]</a>
<a class="ltx_ref" href="#eq1">Equation (1)</a>
</p></div><table class="ltx_table" id="tab1"><caption>Table A</caption><tr><td>1</td></tr></table>
<figure class="ltx_figure" id="fig1"><figcaption class="ltx_caption">An image</figcaption>
<img src="assets/figure.png"></figure>
<div class="ltx_equation" id="eq1"><math><mi>x</mi></math></div>
</section><ul><li class="ltx_bibitem" id="bib1">Source A</li></ul>
<div class="ltx_theorem">Unknown theorem content</div>
<script>document.write('must not execute')</script></article></body></html>'''


class NormalizationTests(unittest.TestCase):
    def normalize_xml(self, data=XML):
        return normalize_latexml_xml(data, bundle_id="a"*64, root_path="paper.tex",
                                     provenance={"run_id": "b"*32}, engine={"name": "LaTeXML"})

    def normalize_html(self, data=HTML):
        return normalize_latexml_html(data, bundle_id="a"*64, root_path="paper.tex",
                                      provenance={"run_id": "b"*32}, engine={"name": "ar5ivist"})

    def test_xml_structure_and_node_hierarchy(self):
        d = self.normalize_xml()
        by_kind = {}
        for n in d.nodes:
            by_kind.setdefault(n.kind, []).append(n)
        self.assertEqual(by_kind["section"][0].title, "Introduction")
        self.assertIn("paragraph_text", by_kind)
        self.assertEqual(by_kind["paragraph_text"][0].parent_id, by_kind["section"][0].id)
        self.assertIn(by_kind["paragraph_text"][0].id, by_kind["section"][0].children)
        self.assertEqual(by_kind["bibliography_item"][0].text, "Source A")
        self.assertIsNone(by_kind["section"][0].source_ref)
        self.assertEqual(d.quality_status, "NOT_EVALUATED")

    def test_xml_math_preserves_tex_and_mathml(self):
        d = self.normalize_xml()
        self.assertEqual(len(d.equations), 2)
        self.assertEqual([e.source_tex for e in d.equations], ["E=mc^2", "x+y"])
        self.assertTrue(all("<" in (e.presentation_mathml or "") for e in d.equations))
        self.assertTrue(all(not e.verified for e in d.equations))

    def test_xml_asset_and_bibliography_edges(self):
        d = self.normalize_xml()
        self.assertEqual(len([a for a in d.assets if a.kind == "figure"]), 1)
        self.assertEqual(len([a for a in d.assets if a.kind == "table"]), 1)
        self.assertEqual(d.assets[0].caption, "A diagram")
        self.assertEqual(d.assets[0].href, "images/diagram.png")
        self.assertEqual(d.assets[0].availability, "NOT_CHECKED")
        self.assertEqual(len(d.citations), 2)
        self.assertTrue(all(r.resolution == "RESOLVED" for r in d.relations))
        self.assertEqual({r.kind for r in d.relations}, {"references", "cites"})

    def test_xml_unknown_semantic_structure_preserved(self):
        d = self.normalize_xml()
        self.assertEqual(len(d.unknown_nodes), 1)
        self.assertEqual(d.unknown_nodes[0].tag, "theorem")
        self.assertIn("Nonstandard scientific structure", d.unknown_nodes[0].raw_markup)

    def test_deterministic_ids_and_document_serialization(self):
        a, b = self.normalize_xml(), self.normalize_xml()
        self.assertEqual(a.to_dict(), b.to_dict())
        self.assertEqual(a.schema_version, "1.0")
        self.assertEqual(a.document_id, b.document_id)
        self.assertEqual(json.loads(json.dumps(a.to_dict()))["quality_status"], "NOT_EVALUATED")

    def test_xml_rejects_dtd_entities_and_invalid_markup(self):
        for source in (b'<!DOCTYPE x [<!ENTITY secret "X">]><document/>',
                       b'<document><broken></document>', b'', b'junk'):
            with self.subTest(source=source[:30]), self.assertRaises(InvalidScientificMarkup):
                self.normalize_xml(source)

    def test_xml_rejects_excessive_structure(self):
        source = b"<document>" + b"<p>"*130 + b"hi" + b"</p>"*130 + b"</document>"
        with self.assertRaises(InvalidScientificMarkup):
            self.normalize_xml(source)

    def test_html_section_math_and_citation_edges(self):
        d = self.normalize_html()
        self.assertEqual(d.source_kind, "latex_html")
        self.assertTrue(any(n.kind == "section" and n.title == "Introduction" for n in d.nodes))
        self.assertEqual(len(d.equations), 2)
        self.assertIsNone(d.equations[0].source_tex)
        self.assertIn("HTML_DOM_RECONSTRUCTED", d.warnings[0])
        self.assertEqual(len([a for a in d.assets if a.kind == "figure"]), 1)
        self.assertIn("RESOLVED", [r.resolution for r in d.relations])
        self.assertTrue(any(x.tag == "div" for x in d.unknown_nodes))
        self.assertNotIn("must not execute", json.dumps(d.to_dict()))

    def test_html_unresolved_references_remain_unresolved(self):
        data = b'<html><p class="ltx_p"><a class="ltx_ref" href="#missing">[?]</a></p></html>'
        d = self.normalize_html(data)
        self.assertEqual(d.relations[0].resolution, "UNRESOLVED")
        self.assertEqual(d.relations[0].requested_target, "#missing")

    def test_unsafe_asset_urls_not_retrieved(self):
        self.assertEqual(classify_asset_href("https://remote.example/image.png"), "EXTERNAL_UNFETCHED")
        self.assertEqual(classify_asset_href("file:///etc/passwd"), "UNSAFE_OR_INLINE")
        self.assertEqual(classify_asset_href("../private.png"), "UNSAFE_PATH")
        self.assertEqual(classify_asset_href("images/a.png"), "NOT_CHECKED")

    def test_external_targets_are_not_resolved_locally(self):
        for v in ("https://example.org/#bib1", "paper2.html#bib1", "../x", "mailto:x@site.org"):
            self.assertIsNone(normalized_target(v))
        self.assertEqual(normalized_target("#bib1"), "bib1")


if __name__ == "__main__":
    unittest.main()
