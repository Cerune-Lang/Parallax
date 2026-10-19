#!/usr/bin/env python3
"""Function-boundary array semantics with a separate Python expected-result model."""
import argparse
from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
import tempfile

from seeded import assess

COUNT = 24


@dataclass(frozen=True)
class FunctionCase:
    kind: int
    mode: int
    values: tuple
    replacement: int
    index: int

    def source(self):
        a,b,c = self.values
        typ = "[i64; 3]" if self.kind == 0 else "[i64]"
        literal = f"[{a}, {b}, {c}]"
        initializer = literal if self.kind == 0 else f"array_copy({literal})"
        lines = [
            f"fn edit(input: {typ}, index: i64, replacement: i64) -> {typ} {{",
            f"    mut local: {typ} = input;",
            "    local[index] = replacement;",
            '    print("edited");',
            "    return local;",
            "}",
            f"fn forward(input: {typ}) -> {typ} {{",
            '    print("forward");',
            "    return input;",
            "}",
            "fn left() -> i64 {",
            '    print("left");',
            "    return 7;",
            "}",
            "fn right() -> i64 {",
            '    print("right");',
            "    return 1 / 0;",
            "}",
            f"fn select(first: i64, input: {typ}, last: i64) -> {typ} {{",
            '    print("body");',
            "    return input;",
            "}",
            f"mut original: {typ} = {initializer};",
            'print("begin");',
        ]
        if self.mode == 0:
            lines += [
                f"edited: {typ} = edit(original, {self.index}, {self.replacement});",
                "print(original);", "print(edited);",
            ]
        elif self.mode == 1:
            lines += [
                f"mut returned: {typ} = forward(original);",
                f"returned[{self.index}] = {self.replacement};",
                "print(original);", "print(returned);",
            ]
        elif self.mode == 2:
            lines += [
                f"edited: {typ} = forward(edit(original, {self.index}, {self.replacement}));",
                "print(original);", "print(edited);",
            ]
        elif self.mode == 3:
            lines += [
                f"edited: {typ} = edit(original, {self.index}, {self.replacement});",
                "print(original);", "print(edited);",
            ]
        elif self.mode == 4:
            lines += [f"unused: {typ} = select(left(), original, right());"]
        elif self.mode == 5:
            lines += [f"selected: {typ} = select(left(), original, 9);",
                      "print(original);", "print(selected);"]
        else:
            raise ValueError("unsupported mode")
        lines += ['print("end");', ""]
        return "\n".join(lines)

    def oracle(self):
        output = ["begin"]
        initial = list(self.values)
        changed = list(self.values)
        if self.mode in (0, 2, 3):
            if not 0 <= self.index < 3:
                return {"kind": "failure", "code": "array-index-out-of-bounds",
                        "stdout": "begin\n"}
            changed[self.index] = self.replacement
            output.append("edited")
            if self.mode == 2:
                output.append("forward")
        elif self.mode == 1:
            output.append("forward")
            changed[self.index] = self.replacement
        elif self.mode == 4:
            return {"kind": "failure", "code": "division-by-zero",
                    "stdout": "begin\nleft\nright\n"}
        elif self.mode == 5:
            output += ["left", "body"]
        output += [str(initial).replace("'", ""), str(initial if self.mode == 5 else changed), "end"]
        return {"kind": "success", "stdout": "\n".join(output) + "\n"}


def decode(text):
    try:
        fields = [int(line) for line in text.splitlines()]
    except ValueError as exc:
        raise ValueError("noninteger protocol field") from exc
    if fields[:2] != [1, COUNT] or len(fields) != 2 + COUNT * 7:
        raise ValueError("invalid protocol header or length")
    cases = []
    for p in range(2, len(fields), 7):
        kind, mode, a, b, c, replacement, index = fields[p:p+7]
        if kind not in (0, 1) or mode not in range(6):
            raise ValueError("unknown case kind/mode")
        if any(not (-2**63 <= n < 2**63) for n in (a,b,c,replacement,index)):
            raise ValueError("value outside i64 range")
        if not -1 <= index <= 3:
            raise ValueError("index outside protocol range")
        cases.append(FunctionCase(kind, mode, (a,b,c), replacement, index))
    if {c.kind for c in cases} != {0,1} or {c.mode for c in cases} != set(range(6)):
        raise ValueError("incomplete corpus")
    return cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--generator", type=Path, default=Path("cerune/generate_functions.ceru"))
    args = parser.parse_args()
    binary = args.binary.resolve()
    if not binary.is_file():
        parser.error("missing Cerune binary")
    try:
        result = subprocess.run([str(binary), "run", str(args.generator.resolve())],
                                stdin=subprocess.DEVNULL, capture_output=True,
                                timeout=15, check=False)
        if result.returncode or result.stderr:
            raise ValueError(f"generator failure: {result.stderr[:300]!r}")
        cases = decode(result.stdout.decode("utf-8"))
        failures = 0
        with tempfile.TemporaryDirectory(prefix="parallax-function-") as temporary:
            scratch = Path(temporary) / "case.ceru"
            for i, case in enumerate(cases):
                mismatch = assess(case, binary, scratch, 3)
                if mismatch:
                    print(f"FAIL function case {i}: {mismatch}", file=sys.stderr)
                    failures += 1
        print(f"Checked {len(cases)} function-boundary cases; discrepancies: {failures}")
        return int(failures > 0)
    except (OSError, ValueError, UnicodeError, subprocess.TimeoutExpired) as exc:
        print(f"FAIL function generator: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
