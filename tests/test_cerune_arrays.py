import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from cerune_arrays import ArrayCase, decode, COUNT

class ArrayTests(unittest.TestCase):
    def test_copy_is_independent(self):
        case=ArrayCase(0,0,(4,8,12),99,1)
        self.assertEqual(case.oracle()["stdout"],"begin\n[4, 99, 12]\n[4, 8, 12]\nend\n")
        self.assertIn("mut saved: [i64; 3] = original;",case.source())
    def test_dynamic_copy_is_independent(self):
        case=ArrayCase(1,1,(4,8,12),99,1)
        self.assertEqual(case.oracle()["stdout"],"begin\n[4, 8, 12]\n[4, 99, 12]\nend\n")
        self.assertIn("array_copy(",case.source())
    def test_read_and_bounds(self):
        self.assertEqual(ArrayCase(0,2,(4,8,12),99,2).oracle()["stdout"],"begin\n12\n[4, 8, 12]\n[4, 8, 12]\nend\n")
        for mode,index in [(3,-1),(4,3),(5,-1),(6,3)]:
            self.assertEqual(ArrayCase(0,mode,(4,8,12),99,index).oracle(),
                {"kind":"failure","code":"array-index-out-of-bounds","stdout":"begin\n"})
    def test_rhs_not_evaluated_on_bad_index(self):
        self.assertEqual(ArrayCase(1,7,(4,8,12),99,1).oracle()["code"],"division-by-zero")
    def test_protocol(self):
        rows=[(i//8%2,i%8,1,2,3,44,(-1 if i%8 in (3,5) else 3 if i%8 in (4,6) else 1)) for i in range(COUNT)]
        protocol="\n".join(map(str,[1,COUNT,*(x for row in rows for x in row)]))+"\n"
        self.assertEqual(len(decode(protocol)),COUNT)
        for bad in ("",protocol+"0\n",protocol.replace("1\n32\n","2\n32\n",1)):
            with self.assertRaises(ValueError):
                decode(bad)
if __name__=="__main__":
    unittest.main()
