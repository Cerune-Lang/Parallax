#!/usr/bin/env python3
"""Validate Cerune-generated control-flow inputs with an independent Python oracle."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

from control_flow import BoolLiteral, Comparison, FlowCase, Logical
from expressions import Binary, Leaf
from seeded import OPS, assess

COMPARISONS = ("==", "!=", "<", "<=", ">", ">=")
LOGICALS = ("&&", "||")
COUNT = 24


def decode(text):
    lines = text.splitlines()
    if len(lines) != 2 + COUNT * 9:
        raise ValueError("invalid protocol length")
    try:
        numbers = [int(line) for line in lines]
    except ValueError as error:
        raise ValueError("invalid integer field") from error
    if numbers[:2] != [1, COUNT]:
        raise ValueError("invalid protocol header")
    cases = []
    for pos in range(2, len(numbers), 9):
        outer_op, outer_guard, inner_op, inner_guard, cmp, op, a, b, target = numbers[pos:pos + 9]
        if outer_op not in (0, 1) or inner_op not in (0, 1):
            raise ValueError("invalid logical operation")
        if outer_guard not in (0, 1) or inner_guard not in (0, 1):
            raise ValueError("invalid boolean")
        if not (0 <= cmp < len(COMPARISONS) and 0 <= op < len(OPS)):
            raise ValueError("invalid arithmetic or comparison operation")
        if not all(-2**31 <= v <= 2**31-1 for v in (a, b, target)):
            raise ValueError("operand outside i32 range")
        predicate = Comparison(COMPARISONS[cmp], Binary(OPS[op], Leaf(a), Leaf(b)), Leaf(target))
        inner = Logical(LOGICALS[inner_op], BoolLiteral(bool(inner_guard)), predicate)
        condition = Logical(LOGICALS[outer_op], BoolLiteral(bool(outer_guard)), inner)
        cases.append(FlowCase(condition))
    return cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--generator", type=Path, default=Path("cerune/generate_flow.ceru"))
    args = parser.parse_args()
    binary = args.binary.resolve()
    if not binary.is_file():
        parser.error("Cerune executable not found")
    try:
        output = subprocess.run(
            [str(binary), "run", str(args.generator.resolve())],
            stdin=subprocess.DEVNULL, capture_output=True, timeout=15, check=False,
        )
        if output.returncode != 0 or output.stderr:
            raise ValueError("Cerune generator failed")
        cases = decode(output.stdout.decode("utf-8"))
        # Require the corpus to exercise both skipped and evaluated invalid expressions.
        oracles = [case.oracle() for case in cases]
        if not any(o["kind"] == "failure" and o["code"] == "division-by-zero" for o in oracles):
            raise ValueError("missing evaluated trap cases")
        if not any(o["kind"] == "success" for o in oracles):
            raise ValueError("missing successful branch cases")
        with tempfile.TemporaryDirectory(prefix="parallax-flow-") as temp:
            scratch = Path(temp) / "case.ceru"
            failures = 0
            for i, case in enumerate(cases):
                mismatch = assess(case, binary, scratch, 3)
                if mismatch:
                    failures += 1
                    print(f"FAIL Cerune-generated flow case #{i}: {mismatch}", file=sys.stderr)
        print(f"Checked {len(cases)} Cerune-generated flow cases; discrepancies: {failures}")
        return int(failures != 0)
    except (OSError, UnicodeError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"FAIL flow generator: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
