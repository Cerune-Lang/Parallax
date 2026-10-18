import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from control_flow import (BoolLiteral, Comparison, Logical, Negation, FlowCase,
                          eval_bool, generate, minimize, make_bad_predicate)
from expressions import Binary, Leaf

class FlowTests(unittest.TestCase):
    def test_short_circuit(self):
        bad = make_bad_predicate()
        self.assertEqual(FlowCase(Logical("&&", BoolLiteral(False), bad)).oracle(), {"kind":"success","stdout":"entered\nelse\nend\n"})
        self.assertEqual(FlowCase(Logical("||", BoolLiteral(True), bad)).oracle(), {"kind":"success","stdout":"entered\nthen\nend\n"})
        self.assertEqual(FlowCase(Logical("&&", BoolLiteral(True), bad)).oracle()["code"], "division-by-zero")
        self.assertEqual(FlowCase(Logical("||", BoolLiteral(False), bad)).oracle()["code"], "division-by-zero")

    def test_nested_boolean_and_branch_output(self):
        tree = Logical("&&", Negation(BoolLiteral(False)), Comparison("<", Leaf(1), Leaf(2)))
        case = FlowCase(tree)
        self.assertEqual(case.oracle()["stdout"], "entered\nthen\nend\n")
        self.assertIn("if ", case.source())

    def test_deterministic_generation(self):
        self.assertEqual(list(generate(1337, 24, 3)), list(generate(1337, 24, 3)))
        self.assertNotEqual(list(generate(1337, 24, 3)), list(generate(1234, 24, 3)))

    def test_minimize(self):
        case = FlowCase(Logical("&&", BoolLiteral(True), Comparison("==", Leaf(3), Leaf(3))))
        signature = (("run-vm", "oracle-mismatch"),)
        def probe(candidate):
            return signature if candidate.oracle()["kind"] == "success" else ()
        small, attempts = minimize(case, signature, probe, budget=32)
        self.assertLess(len(small.source()), len(case.source()))
        self.assertEqual(probe(small), signature)
        self.assertLessEqual(attempts, 32)

if __name__ == "__main__": unittest.main()
