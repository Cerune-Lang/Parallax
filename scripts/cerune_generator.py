#!/usr/bin/env python3
"""Run the Cerune input generator, then independently check its cases."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile
from seeded import Case, OPS, assess

def decode(text):
    lines = text.splitlines()
    if len(lines) != 36:
        raise ValueError(f"expected 36 lines, got {len(lines)}")
    values = [int(line) for line in lines]
    cases = []
    for i in range(0, len(values), 3):
        left, op, right = values[i:i + 3]
        if not (-100 <= left <= 100 and 0 <= op < len(OPS) and -100 <= right <= 100):
            raise ValueError("invalid generator output")
        cases.append(Case(left, OPS[op], right))
    return cases

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--generator", type=Path, default=Path("cerune/generate.ceru"))
    args = parser.parse_args()
    binary = args.binary.resolve()
    try:
        result = subprocess.run([str(binary), "run", str(args.generator.resolve())],
                                input=b"", capture_output=True, timeout=15, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"generator failed: {result.stderr[:500]!r}")
        cases = decode(result.stdout.decode("utf-8"))
        with tempfile.TemporaryDirectory(prefix="parallax-generator-") as temporary:
            scratch = Path(temporary) / "case.ceru"
            for index, case in enumerate(cases):
                mismatch = assess(case, binary, scratch, 3)
                if mismatch:
                    print(f"FAIL generated case {index}: {mismatch}", file=sys.stderr)
                    return 1
    except (OSError, ValueError, UnicodeError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"FAIL Cerune generator: {exc}", file=sys.stderr)
        return 1
    print(f"PASS Cerune-generated cases: {len(cases)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
