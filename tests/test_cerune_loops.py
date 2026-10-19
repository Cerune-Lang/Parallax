import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from cerune_loops import COUNT, LoopCase, decode


def protocol(rows):
    return "\n".join(map(str, [1, COUNT, *(field for row in rows for field in row)])) + "\n"


class LoopModelTests(unittest.TestCase):
    def test_add_trace(self):
        self.assertEqual(LoopCase(0, 2, 3, 3, 1).oracle(),
                         {"kind": "success", "stdout": "begin\n5\n8\n11\nend\n11\n"})

    def test_multiply_overflow_has_prior_output(self):
        self.assertEqual(LoopCase(1, 1073741824, 2, 3, 1).oracle(),
                         {"kind": "failure", "code": "integer-overflow", "stdout": "begin\n"})

    def test_continue_advances_index(self):
        self.assertEqual(LoopCase(2, 1, 3, 5, 1).oracle()["stdout"],
                         "begin\n4\n7\nend\n7\n")

    def test_break_stops_before_update(self):
        self.assertEqual(LoopCase(3, 1, 2, 6, 3).oracle()["stdout"],
                         "begin\n3\n5\nend\n5\n")

    def test_alternating_updates(self):
        self.assertEqual(LoopCase(4, 2, 3, 4, 1).oracle()["stdout"],
                         "begin\n5\n15\n18\n54\nend\n54\n")

    def test_zero_iterations(self):
        self.assertEqual(LoopCase(0, -3, 9, 0, 1).oracle()["stdout"],
                         "begin\nend\n-3\n")

    def test_decode_rejects_bad_input(self):
        valid = [(i % 5, 1, 2, 3, 2) for i in range(COUNT)]
        self.assertEqual(len(decode(protocol(valid))), COUNT)
        bad = [protocol(valid) + "0\n", "", "1\n1\n",
               protocol([(9, 1, 2, 3, 2)] + valid[1:]),
               protocol([(0, 1, 2, 10, 2)] + valid[1:]),
               protocol([(0, 1, 2, 3, 0)] + valid[1:]),
               protocol([(0, 2**32, 2, 3, 2)] + valid[1:])]
        for payload in bad:
            with self.subTest(payload=payload[:24]):
                with self.assertRaises(ValueError):
                    decode(payload)


if __name__ == "__main__":
    unittest.main()
