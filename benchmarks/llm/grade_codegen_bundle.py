#!/usr/bin/env python3
"""Grade a Kaggle output bundle in an externally isolated execution environment.

WARNING: This script executes generated code using the Cerune CLI. Use a
network-disabled, unprivileged container with memory/CPU limits, not your normal
desktop. The --allow-execution switch is only an explicit acknowledgement.
"""
import argparse
import json
from pathlib import Path
import sys

from codegen_eval import CASES, grade_source


def score_bundle(data, binary, timeout):
    if not isinstance(data, dict) or data.get("experiment") != "cerune-codegen-v1":
        raise ValueError("expected cerune-codegen-v1 result bundle")
    records = data.get("records")
    if not isinstance(records, list) or len(records) != 6:
        raise ValueError("expected six records")
    seen = set()
    results = []
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("invalid record")
        task = record.get("task")
        condition = record.get("condition")
        if task not in CASES or condition not in ("baseline", "spec"):
            raise ValueError("unknown task or condition")
        key = (task, condition)
        if key in seen:
            raise ValueError("duplicate task and condition")
        seen.add(key)
        source = record.get("response")
        if not isinstance(source, str):
            raise ValueError("missing model response")
        try:
            result = grade_source(binary, task, source, timeout)
        except ValueError as err:
            result = {
                "task": task, "passed": 0, "total": len(CASES[task]["tests"]),
                "score": 0.0, "all_pass": False,
                "diagnostics": [{"phase": "invalid-source", "reason": str(err)}]
            }
        results.append({
            "task": task,
            "condition": condition,
            "passed": result["passed"],
            "total": result["total"],
            "score": result["score"],
            "all_pass": result["all_pass"],
            "diagnostics": result["diagnostics"],
        })
    output = {}
    for condition in ("baseline", "spec"):
        group = [r for r in results if r["condition"] == condition]
        output[condition] = {
            "full_pass_tasks": sum(r["all_pass"] for r in group),
            "total_tasks": len(group),
            "individual_tests_passed": sum(r["passed"] for r in group),
            "individual_tests_total": sum(r["total"] for r in group),
        }
    return {"experiment": "cerune-codegen-v1", "results": results, "summary": output}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--responses", type=Path, required=True)
    p.add_argument("--binary", type=Path, required=True)
    p.add_argument("--timeout", type=int, default=3)
    p.add_argument("--allow-execution", action="store_true")
    p.add_argument("--out", type=Path, default=Path("cerune_codegen_scores.json"))
    args = p.parse_args()
    if not args.allow_execution:
        p.error("execution of untrusted model-generated code requires --allow-execution in an isolated container")
    if not 1 <= args.timeout <= 30:
        p.error("--timeout must be 1..30")
    bundle = json.loads(args.responses.read_text(encoding="utf-8"))
    result = score_bundle(bundle, args.binary, args.timeout)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))
    print(f"Saved graded results to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
