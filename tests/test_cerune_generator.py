import unittest
from pathlib import Path

class GeneratorShapeTest(unittest.TestCase):
    def test_template_exists(self):
        source = (Path(__file__).resolve().parents[1] / "cerune/generate.ceru").read_text()
        self.assertIn("while i < 12", source)
        self.assertIn("print(left);", source)
        self.assertIn("print(right);", source)

if __name__ == "__main__": unittest.main()
