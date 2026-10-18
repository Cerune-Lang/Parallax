import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from cerune_generator import decode

class GeneratorProtocolTests(unittest.TestCase):
    def test_valid_protocol(self):
        cases = decode("2\n0\n3\n" * 12)
        self.assertEqual(len(cases), 12)
        self.assertEqual(cases[0].oracle()["stdout"], "5\n")

    def test_short_response(self):
        with self.assertRaises(ValueError):
            decode("0\n")

    def test_invalid_operator(self):
        with self.assertRaises(ValueError):
            decode("2\n9\n3\n" * 12)

if __name__ == "__main__":
    unittest.main()
