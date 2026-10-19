#!/usr/bin/env python3
"""Check Cerune-generated bounded stateful loops against an independent Python model."""
import argparse
from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
import tempfile

from seeded import assess

COUNT = 30
MIN_I32, MAX_I32 = -(2 ** 31), 2 ** 31 - 1


@dataclass(frozen=True)
class LoopCase:
    mode: int
    start: int
    step: int
    rounds: int
    stop: int

    def source(self):
        body = []
        if self.mode == 3:
            body.append("    if i == stop - 1 { break; }")
        if self.mode == 2:
            body.append("    if i % 2 == 0 { i = i + 1; continue; }")
        if self.mode == 1:
            body.append("    value = value * step;")
        elif self.mode == 4:
            body.append("    if i % 2 == 0 { value = value + step; } else { value = value * step; }")
        else:
            body.append("    value = value + step;")
        body += ["    print(value);", "    i = i + 1;"]
        return "\n".join([
            f"mut value: i32 = {self.start};",
            f"step: i32 = {self.step};",
            f"rounds: i64 = {self.rounds};",
            f"stop: i64 = {self.stop};",
            "mut i: i64 = 0;",
            'print("begin");',
            "while i < rounds {", *body, "}",
            'print("end");', "print(value);", "",
        ])

    def oracle(self):
        value = self.start
        output = ["begin"]
        for i in range(self.rounds):
            if self.mode == 3 and i == self.stop - 1:
                break
            if self.mode == 2 and i % 2 == 0:
                continue
            result = value * self.step if (
                self.mode == 1 or (self.mode == 4 and i % 2 == 1)
            ) else value + self.step
            if result < MIN_I32 or result > MAX_I32:
                return {"kind": "failure", "code": "integer-overflow",
                        "stdout": "\n".join(output) + "\n"}
            value = result
            output.append(str(value))
        output.extend(("end", str(value)))
        return {"kind": "success", "stdout": "\n".join(output) + "\n"}


def decode(text):
    lines = text.splitlines()
    if len(lines) != 2 + COUNT * 5:
        raise ValueError("unexpected protocol length")
    try:
        fields = [int(line) for line in lines]
    except ValueError as error:
        raise ValueError("noninteger protocol field") from error
    if fields[:2] != [1, COUNT]:
        raise ValueError("unexpected protocol header")
    cases = []
    for i in range(2, len(fields), 5):
        mode, start, step, rounds, stop = fields[i:i + 5]
        if not (0 <= mode <= 4 and MIN_I32 <= start <= MAX_I32 and
                MIN_I32 <= step <= MAX_I32 and 0 <= rounds <= 8 and 1 <= stop <= 9):
            raise ValueError("out-of-range protocol field")
        cases.append(LoopCase(mode, start, step, rounds, stop))
    if {case.mode for case in cases} != set(range(5)):
        raise ValueError("missing transition mode")
    return cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--generator", type=Path, default=Path("cerune/generate_loops.ceru"))
    args = parser.parse_args()
    binary = args.binary.resolve()
    if not binary.is_file():
        parser.error("Cerune binary not found")
    try:
        generated = subprocess.run(
            [str(binary), "run", str(args.generator.resolve())],
            stdin=subprocess.DEVNULL, capture_output=True, timeout=15, check=False,
        )
        if generated.returncode or generated.stderr:
            raise ValueError(f"generator execution failed: {generated.stderr[:300]!r}")
        cases = decode(generated.stdout.decode("utf-8"))
        expectations = [case.oracle() for case in cases]
        if not any(o["kind"] == "failure" for o in expectations):
            raise ValueError("missing overflow coverage")
        if not any(case.rounds == 0 for case in cases):
            raise ValueError("missing zero-iteration coverage")
        failures = 0
        with tempfile.TemporaryDirectory(prefix="parallax-loops-") as tmp:
            scratch = Path(tmp) / "case.ceru"
            for i, case in enumerate(cases):
                difference = assess(case, binary, scratch, 3)
                if difference:
                    failures += 1
                    print(f"FAIL stateful loop #{i}: {difference}", file=sys.stderr)
        print(f"Checked {len(cases)} Cerune-generated stateful loops; discrepancies: {failures}")
        return int(failures != 0)
    except (OSError, ValueError, UnicodeError, subprocess.TimeoutExpired) as error:
        print(f"FAIL loop generator: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
