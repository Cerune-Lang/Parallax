"""Pure, non-executing contract checks for Kaggle generation collection."""
import ast
import pathlib
import sys
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1] / "benchmarks" / "llm"
sys.path.insert(0, str(ROOT))
import grade_codegen_bundle


class CodeGenerationBundleTests(unittest.TestCase):
    def test_collection_source_compiles(self):
        code = (ROOT / "kaggle_codegen_collect.py").read_text(encoding="utf-8")
        ast.parse(code)
        self.assertIn("with kbench.chats.new(", code)
        self.assertNotIn("subprocess.run(", code)
        self.assertIn('"status": "captured-not-graded"', code)

    def test_six_response_results(self):
        bundle = {
            "experiment": "cerune-codegen-v1",
            "records": [
                {"condition": condition, "task": task, "response": "fn solve(x: i64) -> i64 { return x; }"}
                for condition in ("baseline", "spec")
                for task in ("abs", "clamp", "sum_squares")
            ]
        }
        def pretend_grade(_binary, task, _source, _timeout):
            return {"task": task, "passed": 2, "total": 5, "score": 0.4, "all_pass": False, "diagnostics": []}
        with patch.object(grade_codegen_bundle, "grade_source", side_effect=pretend_grade):
            result = grade_codegen_bundle.score_bundle(bundle, pathlib.Path("unused"), 3)
        self.assertEqual(len(result["results"]), 6)
        self.assertEqual(result["summary"]["baseline"]["individual_tests_passed"], 6)
        self.assertEqual(result["summary"]["spec"]["individual_tests_total"], 15)

    def test_reject_duplicate_records(self):
        data = {
            "experiment": "cerune-codegen-v1",
            "records": [{"task": "abs", "condition": "baseline", "response": "code"}] * 6,
        }
        with patch.object(grade_codegen_bundle, "grade_source", return_value={
            "task": "abs", "passed": 0, "total": 7, "score": 0., "all_pass": False, "diagnostics": []
        }), self.assertRaisesRegex(ValueError, "duplicate"):
            grade_codegen_bundle.score_bundle(data, pathlib.Path("unused"), 3)


if __name__ == "__main__":
    unittest.main()
