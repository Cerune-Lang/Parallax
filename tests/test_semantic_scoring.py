"""Tests verifying that semantic scoring never hides actual wrong answers."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks" / "llm"))
from semantic_scoring import compare_prediction, normalize_semantic_response


class SemanticScoringTests(unittest.TestCase):
    def test_exact(self):
        self.assertEqual(compare_prediction("OK:20,99", "OK:20,99"),
                         {"strict": True, "semantic": True})

    def test_code_alias(self):
        self.assertEqual(
            compare_prediction("ERROR:INTEGER_OVERFLOW:5", "ERROR:integer-overflow:5"),
            {"strict": False, "semantic": True}
        )
        self.assertEqual(
            compare_prediction("ERROR:ARRAY_INDEX_OUT_OF_BOUNDS:", "ERROR:array-index-out-of-bounds:"),
            {"strict": False, "semantic": True}
        )

    def test_semantic_errors_still_fail(self):
        wrong = [
            ("OK:99,99", "OK:20,99"),
            ("ERROR:integer-overflow:7", "ERROR:integer-overflow:5"),
            ("ERROR:division-by-zero:5", "ERROR:integer-overflow:5"),
            ("OK:20,99,extra", "OK:20,99"),
            ("ERROR:INTEGER_OVERFLOW:5 extra", "ERROR:integer-overflow:5"),
            ("ERROR:UNKNOWN_ERROR:5", "ERROR:unknown-error:5"),
        ]
        for actual, expected in wrong:
            with self.subTest(actual=actual):
                self.assertFalse(compare_prediction(actual, expected)["semantic"])

    def test_normalization_keeps_printed_case(self):
        self.assertEqual(normalize_semantic_response("ERROR:INTEGER_OVERFLOW:Hello"),
                         "ERROR:integer-overflow:Hello")
        self.assertFalse(
            compare_prediction("ERROR:INTEGER_OVERFLOW:hello", "ERROR:integer-overflow:Hello")["semantic"]
        )


if __name__ == "__main__":
    unittest.main()
