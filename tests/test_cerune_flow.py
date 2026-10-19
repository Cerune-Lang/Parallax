import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from cerune_flow import decode

def protocol(rows):
    return "\n".join(str(v) for v in [1, 24, *(x for row in rows for x in row)]) + "\n"

def row(outer_op=0, outer_guard=1, inner_op=0, inner_guard=1,
        cmp=0, arithmetic=3, a=1, b=0, target=0):
    return (outer_op, outer_guard, inner_op, inner_guard,
            cmp, arithmetic, a, b, target)

class FlowProtocolTests(unittest.TestCase):
    def test_skipped_and_executed_traps(self):
        rows = [row(outer_guard=0), row(outer_op=1), row(inner_guard=0),
                row(outer_op=1, outer_guard=0, inner_op=1),
                row(), row(outer_op=1, outer_guard=0, inner_op=1, inner_guard=0)]
        cases = decode(protocol((rows * 4)))
        kinds = [case.oracle()["kind"] for case in cases[:6]]
        self.assertEqual(kinds, ["success"] * 4 + ["failure"] * 2)
        self.assertEqual(cases[4].oracle(), {"kind": "failure", "code": "division-by-zero", "stdout": "entered\n"})
        self.assertIn("&&", cases[0].source())
        self.assertIn("if ", cases[0].source())

    def test_valid_normal_result(self):
        cases = decode(protocol([row(arithmetic=0, a=1, b=2, target=3)] * 24))
        self.assertEqual(cases[0].oracle()["stdout"], "entered\nthen\nend\n")

    def test_reject_invalid_protocol(self):
        for payload in ("", "1\n24\n", protocol([row()] * 24) + "0\n",
                        protocol([row(outer_guard=2)] * 24),
                        protocol([row(arithmetic=4)] * 24),
                        protocol([row(a=2**31)] * 24),
                        protocol([row(cmp=6)] * 24)):
            with self.subTest(payload=payload[:20]):
                with self.assertRaises(ValueError):
                    decode(payload)

if __name__ == "__main__":
    unittest.main()
