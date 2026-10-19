import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from cerune_nested import decode


def protocol(rows):
    return "\n".join(map(str, [1, len(rows), *(item for row in rows for item in row)])) + "\n"


class NestedProtocolTests(unittest.TestCase):
    def test_normal_nested_expression(self):
        case = decode(protocol([(2, 3, -4, 0, 2)]))[0]
        self.assertEqual(case.oracle(), {"kind": "success", "stdout": "-20\n"})
        self.assertIn("print(((v0 + v1) * v2));", case.source())

    def test_inner_overflow(self):
        case = decode(protocol([(2147483647, 1, 1, 0, 0)]))[0]
        self.assertEqual(case.oracle()["code"], "integer-overflow")

    def test_inner_and_outer_division_by_zero(self):
        cases = decode(protocol([(1, 0, 2, 3, 0), (4, 2, 0, 0, 3)]))
        self.assertEqual([case.oracle()["code"] for case in cases],
                         ["division-by-zero", "division-by-zero"])

    def test_rejects_malformed_protocols(self):
        for bad in ("", "2\n1\n1\n2\n3\n0\n0\n", "1\n0\n",
                    "1\n1\n1\n2\n3\n0\n", "1\n1\n1\n2\n3\n0\n9\n",
                    "1\n1\n2147483648\n2\n3\n0\n0\n", "junk\n"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    decode(bad)

    def test_rejects_extra_fields(self):
        with self.assertRaises(ValueError):
            decode(protocol([(1, 2, 3, 0, 0)]) + "0\n")


if __name__ == "__main__":
    unittest.main()
