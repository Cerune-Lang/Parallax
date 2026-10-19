import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from cerune_functions import FunctionCase, decode, COUNT


class FunctionOracleTests(unittest.TestCase):
    def test_copy_on_function_return(self):
        c = FunctionCase(0, 0, (1, 2, 3), 99, 1)
        self.assertEqual(c.oracle()["stdout"], "begin\nedited\n[1, 2, 3]\n[1, 99, 3]\nend\n")
        self.assertIn("fn edit(input: [i64; 3]", c.source())

    def test_dynamic_return_and_update(self):
        c = FunctionCase(1, 1, (1, 2, 3), 99, 1)
        self.assertEqual(c.oracle()["stdout"], "begin\nforward\n[1, 2, 3]\n[1, 99, 3]\nend\n")
        self.assertIn("fn forward(input: [i64]) -> [i64]", c.source())

    def test_nested_calls(self):
        c = FunctionCase(0, 2, (1, 2, 3), 99, 1)
        self.assertEqual(c.oracle()["stdout"], "begin\nedited\nforward\n[1, 2, 3]\n[1, 99, 3]\nend\n")

    def test_bounds_trap_in_callee(self):
        self.assertEqual(FunctionCase(0, 3, (1, 2, 3), 99, 3).oracle(),
                         {"kind": "failure", "code": "array-index-out-of-bounds", "stdout": "begin\n"})

    def test_argument_order_and_early_trap(self):
        self.assertEqual(FunctionCase(1, 4, (1, 2, 3), 99, 0).oracle(),
                         {"kind": "failure", "code": "division-by-zero", "stdout": "begin\nleft\nright\n"})
        self.assertEqual(FunctionCase(1, 5, (1, 2, 3), 99, 0).oracle()["stdout"],
                         "begin\nleft\nbody\n[1, 2, 3]\n[1, 2, 3]\nend\n")

    def test_protocol(self):
        rows = [(i//12, i%6, 1,2,3,99, 3 if i%6==3 else 1) for i in range(COUNT)]
        encoded = "\n".join(map(str, [1, COUNT, *(x for row in rows for x in row)]))+"\n"
        self.assertEqual(len(decode(encoded)), COUNT)
        for data in ("", encoded+"0\n", encoded.replace("1\n24\n","2\n24\n",1)):
            with self.assertRaises(ValueError):
                decode(data)


if __name__ == "__main__":
    unittest.main()
