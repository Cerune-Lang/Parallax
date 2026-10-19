#!/usr/bin/env python3
"""Independent oracle for Cerune-authored array copy and bounds cases."""
import argparse
from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
import tempfile
from seeded import assess

COUNT = 32

@dataclass(frozen=True)
class ArrayCase:
    kind: int
    mode: int
    values: tuple
    replacement: int
    index: int

    def source(self):
        a,b,c = self.values
        ty = "[i64; 3]" if self.kind == 0 else "[i64]"
        init = f"[{a}, {b}, {c}]" if self.kind == 0 else f"array_copy([{a}, {b}, {c}])"
        statements = [
            f"mut original: {ty} = {init};",
            f"mut saved: {ty} = original;",
            'print("begin");',
        ]
        if self.mode == 0:
            statements += [f"original[{self.index}] = {self.replacement};"]
        elif self.mode == 1:
            statements += [f"saved[{self.index}] = {self.replacement};"]
        elif self.mode in (2,3,4):
            statements += [f"print(original[{self.index}]);"]
        elif self.mode in (5,6):
            statements += [f"original[{self.index}] = {self.replacement};"]
        elif self.mode == 7:
            statements += [f"original[{self.index}] = 1 / 0;"]
        statements += ["print(original);", "print(saved);", 'print("end");', ""]
        return "\n".join(statements)

    def oracle(self):
        original = list(self.values)
        saved = list(self.values)
        stdout = "begin\n"
        if self.mode in (2,3,4):
            if self.index < 0 or self.index >= 3:
                return {"kind":"failure","code":"array-index-out-of-bounds","stdout":stdout}
            stdout += f"{original[self.index]}\n"
        else:
            if self.index < 0 or self.index >= 3:
                return {"kind":"failure","code":"array-index-out-of-bounds","stdout":stdout}
            if self.mode == 7:
                return {"kind":"failure","code":"division-by-zero","stdout":stdout}
            if self.mode == 1:
                saved[self.index] = self.replacement
            else:
                original[self.index] = self.replacement
        show = lambda values: "[" + ", ".join(str(v) for v in values) + "]\n"
        return {"kind":"success", "stdout": stdout + show(original) + show(saved) + "end\n"}

def decode(text):
    try:
        values = [int(line) for line in text.splitlines()]
    except ValueError as exc:
        raise ValueError("invalid integer field") from exc
    if len(values) != 2 + 7*COUNT or values[:2] != [1, COUNT]:
        raise ValueError("invalid protocol header or length")
    cases = []
    for p in range(2, len(values), 7):
        kind, mode, a, b, c, replacement, index = values[p:p+7]
        if kind not in (0,1) or mode not in range(8):
            raise ValueError("invalid kind or mode")
        if any(not (-2**63 <= n < 2**63) for n in (a,b,c,replacement,index)):
            raise ValueError("invalid i64")
        if not (-1 <= index <= 3):
            raise ValueError("invalid index")
        cases.append(ArrayCase(kind,mode,(a,b,c),replacement,index))
    if {case.kind for case in cases} != {0,1} or {case.mode for case in cases} != set(range(8)):
        raise ValueError("incomplete test coverage")
    return cases

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--generator", type=Path, default=Path("cerune/generate_arrays.ceru"))
    args = parser.parse_args()
    binary = args.binary.resolve()
    if not binary.is_file():
        parser.error("Cerune binary not found")
    try:
        output = subprocess.run([str(binary),"run",str(args.generator.resolve())],
                                stdin=subprocess.DEVNULL,capture_output=True,timeout=15,check=False)
        if output.returncode or output.stderr:
            raise ValueError(f"generator failure: {output.stderr[:300]!r}")
        cases = decode(output.stdout.decode("utf-8"))
        errors = 0
        with tempfile.TemporaryDirectory(prefix="parallax-arrays-") as tmp:
            source = Path(tmp)/"case.ceru"
            for i, case in enumerate(cases):
                mismatch = assess(case,binary,source,3)
                if mismatch:
                    errors += 1
                    print(f"FAIL array case {i}: {mismatch}",file=sys.stderr)
        print(f"Checked {len(cases)} array cases; discrepancies: {errors}")
        return int(errors != 0)
    except (OSError,ValueError,UnicodeError,subprocess.TimeoutExpired) as exc:
        print(f"FAIL array generator: {exc}",file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
