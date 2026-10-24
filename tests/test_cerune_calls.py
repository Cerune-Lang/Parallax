import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from cerune_calls import CallCase, ROUTES, assess, decode

def rows():
    return [(mode,3,second if mode in (3,6) else -2)
            for second in (0,1) for mode in range(8)]

def protocol(cases):
    return "\n".join(map(str,[1,len(cases),*(x for row in cases for x in row)]))+"\n"

class CallProtocolTests(unittest.TestCase):
    def test_oracles(self):
        cases=decode(protocol(rows()))
        expected=("1\n","2\n","3\n-2\n1\n","91\n3\n","3\n6\n-2\n","3\ncall!\n","88\n")
        for case, stdout in zip(cases[:7],expected):
            self.assertEqual(case.oracle(),{"kind":"success","stdout":stdout})
        self.assertEqual(cases[7].oracle(),{"kind":"failure","code":"division-by-zero","stdout":"3\n"})
        self.assertEqual(cases[11].oracle()["stdout"],"91\n92\n4\n")
        self.assertEqual(cases[14].oracle()["stdout"],"3\n88\n")

    def test_sources(self):
        cases=decode(protocol(rows()))
        for mode,part in [(1,"twice(add("),(2,"seen(3), seen(-2)"),
                          (3,"if flag == 0 { return value; }"),
                          (4,"copy[0] = copy[0] + delta;"),
                          (5,'concat(text, "!")'),(6,"if skip { return; }"),
                          (7,"seen(1 / 0)")]:
            self.assertIn(part,cases[mode].source())

    def test_invalid_inputs(self):
        original=rows()
        bad=("", "1\n16\n",protocol(original)+"0\n",
             protocol([(8,3,0),*original[1:]]),
             protocol([(0,41,0),*original[1:]]),
             protocol([(0,3,41),*original[1:]]),
             protocol([(1 if mode==0 else mode,a,b) for mode,a,b in original]),
             protocol([(3,3,2) if i==3 else row for i,row in enumerate(original)]),
             protocol([(3,3,0) if i==11 else row for i,row in enumerate(original)]),
             protocol(original).replace("\n3\n","\n3_0\n",1))
        for data in bad:
            with self.subTest(data=data[:25]),self.assertRaises(ValueError):
                decode(data)

    def test_four_routes_and_stdout(self):
        case=CallCase(7,3,0)
        good=subprocess.CompletedProcess([],1,b"3\n",b"cerune: runtime-v1 code=division-by-zero\n")
        bad=subprocess.CompletedProcess([],1,b"",b"cerune: runtime-v1 code=division-by-zero\n")
        with TemporaryDirectory() as temp:
            source=Path(temp)/"case.ceru"
            with patch("cerune_calls.subprocess.run",return_value=good) as run:
                self.assertFalse(assess(case,Path("cerune"),source))
                self.assertEqual(run.call_count,len(ROUTES))
                self.assertEqual(run.call_args_list[2].args[0][1:4],
                                 ["run-mir",str(source),"--ssa"])
            with patch("cerune_calls.subprocess.run",side_effect=[good,bad,good,good]):
                self.assertIn(("MIR","oracle-mismatch"),assess(case,Path("cerune"),source))

if __name__=="__main__":
    unittest.main()
