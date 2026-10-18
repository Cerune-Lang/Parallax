#!/usr/bin/env python3
"""Compare successful Cerune execution routes against a known-output oracle."""
import argparse
from pathlib import Path
import subprocess
import sys

ROUTES = ("run", "run-mir", "run-vm")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--cases", default="cases", type=Path)
    parser.add_argument("--timeout", type=int, default=10)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    cases = sorted(args.cases.glob("*.ceru"))
    if not cases:
        parser.error("no .ceru fixtures found")
    failures = 0
    for case in cases:
        expected_path = case.with_suffix(".expected")
        if not expected_path.is_file():
            print(f"FAIL {case}: expected output file is missing", file=sys.stderr)
            failures += 1
            continue
        expected = expected_path.read_bytes()
        for route in ROUTES:
            try:
                completed = subprocess.run(
                    [str(args.binary.resolve()), route, str(case.resolve())],
                    capture_output=True, timeout=args.timeout, check=False,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                print(f"FAIL {case.name} [{route}]: {exc}", file=sys.stderr)
                failures += 1
                continue
            if completed.returncode != 0 or completed.stdout != expected:
                print(
                    f"FAIL {case.name} [{route}]: exit={completed.returncode}, "
                    f"stdout={completed.stdout!r}, expected={expected!r}, "
                    f"stderr={completed.stderr[:500]!r}", file=sys.stderr,
                )
                failures += 1
            else:
                print(f"PASS {case.name} [{route}]")
    print(f"Checked {len(cases)} fixture(s) across {len(ROUTES)} routes; failures: {failures}")
    return 1 if failures else 0

if __name__ == "__main__":
    sys.exit(main())
