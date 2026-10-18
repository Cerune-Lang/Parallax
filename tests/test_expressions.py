import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from expressions import (Leaf, Binary, Trap, ExpressionCase, evaluate,
                         generate, minimize, size, shrink_candidates)
from seeded import MIN_I32, MAX_I32


class ExpressionTests(unittest.TestCase):
    def test_deterministic_and_bounded(self):
        a = list(generate(1337, 30, 4))
        self.assertEqual(a, list(generate(1337, 30, 4)))
        self.assertNotEqual(a, list(generate(1338, 30, 4)))
        self.assertTrue(all(len(case.source()) < 800 for case in a))

    def test_nested_math(self):
        case = ExpressionCase(Binary("*", Binary("+", Leaf(2), Leaf(3)), Leaf(-4)))
        self.assertEqual(case.oracle(), {"kind": "success", "stdout": "-20\n"})
        self.assertIn("print(((v0 + v1) * v2));", case.source())

    def test_intermediate_overflow_and_evaluation_order(self):
        case = ExpressionCase(Binary("/", Binary("+", Leaf(MAX_I32), Leaf(1)), Leaf(0)))
        self.assertEqual(case.oracle()["code"], "integer-overflow")
        case = ExpressionCase(Binary("+", Leaf(0), Binary("/", Leaf(1), Leaf(0))))
        self.assertEqual(case.oracle()["code"], "division-by-zero")
        case = ExpressionCase(Binary("/", Leaf(MIN_I32), Leaf(-1)))
        self.assertEqual(case.oracle()["code"], "division-overflow")

    def test_reduction_keeps_oracle_and_signature(self):
        original = ExpressionCase(Binary("+", Binary("*", Leaf(42), Leaf(10)), Leaf(30)))
        fingerprint = (("run", "oracle-mismatch"),)
        def probe(candidate):
            return fingerprint if candidate.oracle()["kind"] == "success" else ()
        simplified, attempts = minimize(original, fingerprint, probe, 60)
        self.assertLess(size(simplified), size(original))
        self.assertEqual(probe(simplified), fingerprint)
        self.assertLessEqual(attempts, 60)


if __name__ == "__main__":
    unittest.main()
