#!/usr/bin/env python3
"""Compare success and diagnosed runtime failure across Cerune execution routes."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

ROUTES = ("run", "run-mir", "run-vm")
DIAGNOSTIC = re.compile(rb"(?m)^cerune: runtime-v1 code=([a-z0-9-]+)(?=\s|$)")

def compare_result(result, spec):
    if spec["kind"] == "success":
        return result.returncode == 0 and result.stdout == spec["stdout"].encode() and not result.stderr
    return (
        result.returncode == 1
        and result.stdout == spec["stdout"].encode()
        and DIAGNOSTIC.findall(result.stderr) == [spec["code"].encode("ascii")]
    )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--cases", default="cases", type=Path)
    parser.add_argument("--timeout", default=10, type=int)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    cases = sorted(args.cases.glob("*.ceru"))
    if not cases:
        parser.error("no cases found")
    failures = 0
    for case in cases:
        expected = case.with_suffix(".expected")
        specification = case.with_suffix(".json")
        if specification.exists():
            spec = json.loads(specification.read_text(encoding="utf-8"))
        elif expected.exists():
            spec = {"kind": "success", "stdout": expected.read_text(encoding="utf-8")}
        else:
            print(f"FAIL {case.name}: missing oracle", file=sys.stderr)
            failures += 1
            continue
        results = []
        for route in ROUTES:
            try:
                result = subprocess.run(
                    [str(args.binary.resolve()), route, str(case.resolve()), "--diagnostic-format", "runtime-v1"],
                    stdin=subprocess.DEVNULL, capture_output=True, timeout=args.timeout,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                failures += 1
                print(f"FAIL {case.name} [{route}]: {exc}", file=sys.stderr)
                continue
            if compare_result(result, spec):
                print(f"PASS {case.name} [{route}]")
            else:
                failures += 1
                print(f"FAIL {case.name} [{route}]: exit={result.returncode}, stdout={result.stdout!r}, stderr={result.stderr[:400]!r}, oracle={spec!r}",file=sys.stderr)
            results.append((route, result))
        if len(results) == len(ROUTES):
            signatures = [(r.returncode, r.stdout, tuple(DIAGNOSTIC.findall(r.stderr))) for _,r in results]
            if len(set(signatures)) != 1:
                failures += 1
                print(f"FAIL {case.name}: execution routes disagree",file=sys.stderr)
    print(f"Checked {len(cases)} cases; failures: {failures}")
    return int(failures != 0)

if __name__ == "__main__":
    sys.exit(main())
