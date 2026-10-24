#!/usr/bin/env python3
"""Check Cerune-generated function calls using independent Python expectations."""
import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from differential import DIAGNOSTIC, compare_result

COUNT = 16
ROUTES = (("IR", ("run",)), ("MIR", ("run-mir",)),
          ("SSA", ("run-mir", "--ssa")), ("VM", ("run-vm",)))
DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]*)\Z")

@dataclass(frozen=True)
class CallCase:
    mode: int
    a: int
    b: int

    def source(self):
        a, b = self.a, self.b
        if self.mode == 0:
            return ("fn add(left: i64, right: i64) -> i64 { return left + right; }\n"
                    f"print(add({a}, {b}));\n")
        if self.mode == 1:
            return ("fn add(left: i64, right: i64) -> i64 { return left + right; }\n"
                    "fn twice(value: i64) -> i64 { return add(value, value); }\n"
                    f"print(twice(add({a}, {b})));\n")
        if self.mode == 2:
            return ("fn seen(value: i64) -> i64 { print(value); return value; }\n"
                    "fn add(left: i64, right: i64) -> i64 { return left + right; }\n"
                    f"print(add(seen({a}), seen({b})));\n")
        if self.mode == 3:
            return ("fn decide(value: i64, flag: i64) -> i64 {\n"
                    "    print(91);\n    if flag == 0 { return value; }\n"
                    "    print(92);\n    return value + flag;\n}\n"
                    f"print(decide({a}, {b}));\n")
        if self.mode == 4:
            return ("fn changed(items: [i64; 2], delta: i64) -> [i64; 2] {\n"
                    "    mut copy: [i64; 2] = items;\n"
                    "    copy[0] = copy[0] + delta;\n    return copy;\n}\n"
                    f"original: [i64; 2] = [{a}, {b}];\n"
                    "updated: [i64; 2] = changed(original, 3);\n"
                    "print(original[0]);\nprint(updated[0]);\nprint(original[1]);\n")
        if self.mode == 5:
            return ("fn label(text: string, number: i64) -> string {\n"
                    '    print(number);\n    return concat(text, "!");\n}\n'
                    f'print(label("call", {a}));\n')
        if self.mode == 6:
            skip = "true" if b == 0 else "false"
            return ("fn display(skip: bool, value: i64) -> void {\n"
                    "    if skip { return; }\n    print(value);\n}\n"
                    f"display({skip}, {a});\nprint(88);\n")
        if self.mode == 7:
            return ("fn seen(value: i64) -> i64 { print(value); return value; }\n"
                    "fn add(left: i64, right: i64) -> i64 { return left + right; }\n"
                    f"print(add(seen({a}), seen(1 / 0)));\n")
        raise ValueError("unknown mode")

    def oracle(self):
        a, b = self.a, self.b
        if self.mode == 0: output = f"{a + b}\n"
        elif self.mode == 1: output = f"{2 * (a + b)}\n"
        elif self.mode == 2: output = f"{a}\n{b}\n{a + b}\n"
        elif self.mode == 3:
            output = f"91\n{a}\n" if b == 0 else f"91\n92\n{a + b}\n"
        elif self.mode == 4: output = f"{a}\n{a + 3}\n{b}\n"
        elif self.mode == 5: output = f"{a}\ncall!\n"
        elif self.mode == 6: output = "88\n" if b == 0 else f"{a}\n88\n"
        elif self.mode == 7:
            return {"kind":"failure", "code":"division-by-zero", "stdout":f"{a}\n"}
        else: raise ValueError("unknown mode")
        return {"kind":"success", "stdout":output}

def decode(text):
    lines = text.splitlines()
    if len(lines) != 2 + COUNT * 3 or any(not DECIMAL.fullmatch(x) for x in lines):
        raise ValueError("invalid protocol length or decimal field")
    values = [int(x) for x in lines]
    if values[:2] != [1, COUNT]:
        raise ValueError("invalid protocol header")
    cases = []
    for i in range(2, len(values), 3):
        mode, a, b = values[i:i+3]
        if mode not in range(8) or not (-40 <= a <= 40 and -40 <= b <= 40):
            raise ValueError("invalid call case field")
        if mode in (3,6) and b not in (0,1):
            raise ValueError("invalid early return selector")
        cases.append(CallCase(mode,a,b))
    if any(sum(c.mode == m for c in cases) != 2 for m in range(8)):
        raise ValueError("each mode must appear twice")
    for m in (3,6):
        if {c.b for c in cases if c.mode == m} != {0,1}:
            raise ValueError("missing early return branch")
    return cases

def assess(case, binary, path, timeout=3):
    path.write_text(case.source(), encoding="utf-8")
    expected = case.oracle()
    signatures, failures = [], []
    for label, route in ROUTES:
        cmd = [str(binary),route[0],str(path),*route[1:],"--diagnostic-format","runtime-v1"]
        try:
            result = subprocess.run(cmd, stdin=subprocess.DEVNULL,
                                    capture_output=True, timeout=timeout, check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            failures.append((label,type(exc).__name__))
            continue
        signatures.append((result.returncode,result.stdout,tuple(DIAGNOSTIC.findall(result.stderr))))
        if not compare_result(result, expected):
            failures.append((label,"oracle-mismatch"))
    if len(signatures) == len(ROUTES) and len(set(signatures)) != 1:
        failures.append(("routes","disagreement"))
    return tuple(failures)

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary",type=Path,required=True)
    parser.add_argument("--generator",type=Path,default=Path("cerune/generate_calls.ceru"))
    args = parser.parse_args(argv)
    binary = args.binary.resolve()
    if not binary.is_file():
        parser.error("Cerune executable not found")
    try:
        result = subprocess.run([str(binary),"run",str(args.generator.resolve())],
                                stdin=subprocess.DEVNULL,capture_output=True,timeout=15,check=False)
        if result.returncode or result.stderr:
            raise ValueError(f"generator failed: {result.stderr[:400]!r}")
        cases = decode(result.stdout.decode("utf-8"))
        failures = 0
        with tempfile.TemporaryDirectory(prefix="parallax-calls-") as tmp:
            path = Path(tmp)/"case.ceru"
            for i, case in enumerate(cases):
                mismatch = assess(case,binary,path)
                if mismatch:
                    failures += 1
                    print(f"FAIL call #{i}: {mismatch}",file=sys.stderr)
        print(f"Checked {len(cases)} function-call cases across {len(ROUTES)} routes; discrepancies: {failures}")
        return int(failures != 0)
    except (OSError,ValueError,UnicodeError,subprocess.TimeoutExpired) as exc:
        print(f"FAIL function-call generator: {exc}",file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
