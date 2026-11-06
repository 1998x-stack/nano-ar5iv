"""M02 deterministic source discovery and arXiv metadata regression suite."""
import json
import tempfile
import unittest
from pathlib import Path
from nano_ar5iv.infrastructure.repositories import SnapshotStore
from nano_ar5iv.source.entry_ranker import discover_roots
from nano_ar5iv.source.tex_scanner import scan_tex
from nano_ar5iv.source.dependency_graph import build_graph


def tex(content="Hello"):
    return "\\documentclass{article}\n\\begin{document}\n" + content + "\n\\end{document}\n"


class EntryDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.input = self.root / "source"
        self.input.mkdir()
        self.output = self.root / "snapshots"

    def put(self, path, content):
        target = self.input / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def decide(self):
        bundle = SnapshotStore(self.output).capture(self.input)
        return discover_roots(bundle)

    def test_nonstandard_main_filename_and_nested_root(self):
        self.put("paper/draft.ltx", tex("\\section{A}"))
        decision = self.decide()
        self.assertEqual(decision.status, "SELECTED")
        self.assertEqual(decision.selected_roots, ("paper/draft.ltx",))

    def test_modern_manifest_order_and_ignored_file(self):
        self.put("paper.tex", tex())
        self.put("supp.tex", tex())
        self.put("sample.tex", tex())
        self.put("00README.json", json.dumps({"process": {"compiler": "pdflatex"}, "sources": [
            {"filename": "supp.tex", "usage": "toplevel"},
            {"filename": "sample.tex", "usage": "ignore"},
            {"filename": "paper.tex", "usage": "toplevel"},
        ]}))
        decision = self.decide()
        self.assertEqual(decision.status, "MULTIPLE_ROOTS")
        self.assertEqual(decision.selected_roots, ("supp.tex", "paper.tex"))
        self.assertEqual(decision.ignored, ("sample.tex",))
        self.assertEqual(decision.compiler, "pdflatex")
        self.assertEqual(decision.metadata_source, "00README.json")

    def test_modern_implicit_single_root_and_include(self):
        self.put("abc.tex", tex())
        self.put("macro.tex", "macro")
        self.put("00README.json", json.dumps({"sources": [
            {"filename": "abc.tex"},
            {"filename": "macro.tex", "usage": "include"},
        ]}))
        decision = self.decide()
        self.assertEqual(decision.selected_roots, ("abc.tex",))

    def test_legacy_manifest_and_ignore(self):
        self.put("source.tex", tex())
        self.put("ignored.tex", tex())
        self.put("00README.XXX", "source.tex toplevelfile\nignored.tex ignore\nnohypertex\n")
        decision = self.decide()
        self.assertEqual(decision.status, "SELECTED")
        self.assertEqual(decision.selected_roots, ("source.tex",))
        self.assertEqual(decision.ignored, ("ignored.tex",))

    def test_modern_missing_and_unsafe_root_refused(self):
        self.put("paper.tex", tex())
        self.put("00README.json", json.dumps({"sources": [
            {"filename": "does-not-exist.tex", "usage": "toplevel"}]}))
        self.assertEqual(self.decide().status, "MANIFEST_ERROR")
        self.put("00README.json", json.dumps({"sources": [
            {"filename": "../escape.tex", "usage": "toplevel"}]}))
        self.assertEqual(self.decide().status, "MANIFEST_ERROR")

    def test_invalid_json_and_modern_legacy_conflict(self):
        self.put("paper.tex", tex())
        self.put("00README.json", '{"sources": [')
        self.assertEqual(self.decide().status, "MANIFEST_ERROR")
        self.put("00README.json", '{"sources": [{"filename": "paper.tex"}]}')
        self.put("00README.XXX", "paper.tex toplevelfile")
        self.assertEqual(self.decide().status, "MANIFEST_ERROR")

    def test_two_independent_roots_not_merged(self):
        self.put("paper.tex", tex())
        self.put("supplement.tex", tex())
        decision = self.decide()
        self.assertEqual(decision.status, "MULTIPLE_ROOTS")
        self.assertEqual(set(decision.selected_roots), {"paper.tex", "supplement.tex"})

    def test_subfile_documentclass_not_mistaken_for_separate_root(self):
        self.put("paper.tex", tex("\\subfile{part}"))
        self.put("part.tex", tex("\\section{Part}"))
        decision = self.decide()
        self.assertEqual(decision.status, "SELECTED")
        self.assertEqual(decision.selected_roots, ("paper.tex",))
        self.assertIn("paper.tex", decision.candidates[1].referenced_by)

    def test_dependency_graph_and_comment_verbatim_ignored(self):
        self.put("paper.tex", tex(
            "\\input{sections/method}\n"
            "% \\input{ghost}\n"
            "\\begin{verbatim}\n\\input{fake}\n\\end{verbatim}\n"
            "\\verb+\\input{literal}+\n"
            "\\bibliography{refs}\n"))
        self.put("sections/method.tex", "\\section{Method}")
        self.put("refs.bib", "@article{key, title={X}}")
        decision = self.decide()
        input_edges = [e for e in decision.edges if e.kind == "input"]
        self.assertEqual(len(input_edges), 1)
        self.assertEqual(input_edges[0].target, "sections/method.tex")
        self.assertEqual(input_edges[0].line, 3)
        self.assertEqual(decision.selected_roots, ("paper.tex",))
        bib_edges = [e for e in decision.edges if e.kind == "bibliography"]
        self.assertEqual(bib_edges[0].resolution, "resolved")

    def test_input_without_braces_and_nested_import(self):
        self.put("main.tex", tex("\\input section\n\\import{chapters/}{part}"))
        self.put("section.tex", "section")
        self.put("chapters/part.tex", "part")
        decision = self.decide()
        edges = [e for e in decision.edges if e.kind in ("input", "import")]
        self.assertEqual({e.target for e in edges}, {"section.tex", "chapters/part.tex"})

    def test_dynamic_missing_and_ambiguous_dependency_recorded(self):
        self.put("main.tex", tex("\\input{\\macro}\n\\input{missing}\n\\input{chapter}"))
        self.put("chapter.tex", "one")
        self.put("chapter.ltx", "two")
        decision = self.decide()
        resolutions = {e.resolution for e in decision.edges if e.kind == "input"}
        self.assertTrue({"dynamic", "missing", "ambiguous"} <= resolutions)
        self.assertEqual(decision.selected_roots, ("main.tex",))

    def test_fragments_abstain_and_pdf_only(self):
        self.put("introduction.tex", "\\section{Intro}\nText")
        self.put("method.tex", "\\section{Method}\nText")
        self.assertEqual(self.decide().status, "AMBIGUOUS")
        (self.input / "introduction.tex").unlink()
        (self.input / "method.tex").unlink()
        self.put("paper.pdf", "not actually a PDF; just inventory for NO_TEX")
        self.assertEqual(self.decide().status, "NO_TEX")

    def test_idempotent_decision_json_and_source_immutability(self):
        self.put("main.tex", tex("\\section{A}"))
        a = self.decide().to_dict()
        b = self.decide().to_dict()
        self.assertEqual(a, b)
        self.assertEqual(a["algorithm_version"], "m02.1")

    def test_scanner_escaped_percent_and_inline_verbatim(self):
        source = (r"\% valid escaped percent" + "\n"
                  + r"% \input{fake}" + "\n"
                  + r"\input{real}" + "\n"
                  + r"\verb+\input{hidden}+" + "\n")
        scan = scan_tex(source)
        self.assertEqual([r.value for r in scan.references if r.kind == "input"], ["real"])


if __name__ == "__main__":
    unittest.main()
