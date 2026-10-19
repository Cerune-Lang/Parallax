#!/usr/bin/env python3
"""Decode Cerune-produced nested arithmetic, keeping an independent Python oracle."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

from expressions import Binary, ExpressionCase, Leaf
from seeded import OPS, assess

VERSION = 1
MAX_CASES = 128


def decode(text):
    lines = text.splitlines()
    if len(lines) < 2:
        raise ValueError("missing protocol header")
    try:
        values = [int(line) for line in lines]
    except ValueError as error:
        raise ValueError("noninteger protocol field") from error
    version, count = values[:2]
    if version != VERSION or not 1 <= count <= MAX_CASES:
        raise ValueError("unsupported protocol version or case count")
    if len(values) != 2 + 5 * count:
        raise ValueError("incorrect number of protocol fields")
    cases = []
    for position in range(2, len(values), 5):
        left, right, tail, inner_op, outer_op = values[position:position + 5]
        if not all(-(2 ** 31) <= x <= 2 ** 31 - 1 for x in (left, right, tail)):
            raise ValueError("operand outside i32 range")
        if not (0 <= inner_op < len(OPS) and 0 <= outer_op < len(OPS)):
            raise ValueError("operator outside protocol range")
        cases.append(ExpressionCase(Binary(OPS[outer_op], Binary(OPS[inner_op], Leaf(left), Leaf(right)), Leaf(tail))))
    return cases


def run(binary, generator, timeout=15):
    result = subprocess.run(
        [str(binary), "run", str(generator)],
        stdin=subprocess.DEVNULL,
        capture_output=True, timeout=timeout, check=False,
    )
    if result.returncode != 0 or result.stderr:
        raise ValueError(f"generator failed: status={result.returncode}, stderr={result.stderr[:400]!r}")
    return decode(result.stdout.decode("utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--generator", type=Path, default=Path("cerune/generate_nested.ceru"))
    args = parser.parse_args()
    binary = args.binary.resolve()
    if not binary.is_file():
        parser.error("Cerune executable not found")
    try:
        cases = run(binary, args.generator.resolve())
        with tempfile.TemporaryDirectory(prefix="parallax-nested-") as temporary:
            scratch = Path(temporary) / "current.ceru"
            failures = 0
            for index, case in enumerate(cases):
                fingerprint = assess(case, binary, scratch, 3)
                if fingerprint:
                    print(f"FAIL generated case {index}: {fingerprint}", file=sys.stderr)
                    failures += 1
            print(f"Checked {len(cases)} Cerune-generated expression cases; discrepancies: {failures}")
            return int(failures != 0)
    except (OSError, ValueError, UnicodeError, subprocess.TimeoutExpired) as error:
        print(f"FAIL generator protocol: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
