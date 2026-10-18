import subprocess
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.differential import compare_result

class TestOracle(unittest.TestCase):
    def test_success(self):
        result = subprocess.CompletedProcess([], 0, b"42\n", b"")
        self.assertTrue(compare_result(result, {"kind":"success", "stdout":"42\n"}))
    def test_expected_failure(self):
        result = subprocess.CompletedProcess([], 1, b"before\n", b"cerune: runtime-v1 code=division-by-zero origin=x\n")
        self.assertTrue(compare_result(result, {"kind":"failure", "code":"division-by-zero", "stdout":"before\n"}))
    def test_crash_rejected(self):
        result = subprocess.CompletedProcess([], -11, b"before\n", b"cerune: runtime-v1 code=division-by-zero\n")
        self.assertFalse(compare_result(result, {"kind":"failure", "code":"division-by-zero", "stdout":"before\n"}))

if __name__ == "__main__": unittest.main()
