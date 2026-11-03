#!/usr/bin/env python3
"""Local Cerune code-generation evaluator. Execute only in an isolated runner.

Model-generated code is untrusted input. This CLI deliberately requires an
opt-in before executing it and does not claim to provide a security sandbox.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

SPEC = """Cerune is a typed language. Functions: fn solve(x: i64) -> i64 { return x; }
Local variable: value: i64 = 0; Mutable: mut total: i64 = 0;
Assign using total = total + 1;. Expressions: + - * / %, comparisons, && ||.
Control flow: if x > 0 { return 1; } else { return 0; }
While loop: while x > 0 { x = x - 1; }
For loop: for (mut i: i64 = 0; i < 3; i = i + 1) { ... }
Return type is mandatory, statement terminator is ;, blocks use { }.
The calling program is provided separately. Do NOT write main or print.
"""
EXAMPLE = """Example function (not an evaluation task):
fn increment(x: i64) -> i64 {
    return x + 1;
}
"""

CASES = {
    "clamp": {
        "request": "Return x restricted to the inclusive range 0..100.",
        "tests": [(x, min(100, max(0, x))) for x in (-91, -1, 0, 1, 55, 100, 101, 999)],
    },
    "abs": {
        "request": "Return the nonnegative absolute value of x. Inputs are in [-10000,10000].",
        "tests": [(x, abs(x)) for x in (-9999, -22, -1, 0, 1, 32, 9999)],
    },
    "sum_squares": {
        "request": "For x >= 0, return the sum of i*i for i from 1 through x inclusive. For x < 0 return 0. Test inputs are small.",
        "tests": [(x, sum(i * i for i in range(1, max(0, x) + 1))) for x in (-3, 0, 1, 2, 3, 6, 8)],
    },
}

MAX_SOURCE_BYTES = 8192
BLOCK = re.compile(r"^\\s*```(?:ceru|cerune)?\\s*\\n(.*?)\\n```\\s*$", re.DOTALL | re.IGNORECASE)
FORBIDDEN = re.compile(r"\\b(import|print|main)\\b|\\b(?:std:)\\w+", re.IGNORECASE)
REQUIRED = re.compile(r"\\bfn\\s+solve\\s*\\(\\s*x\\s*:\\s*i64\\s*\\)\\s*->\\s*i64\\s*\\{")
FN = re.compile(r"\\bfn\\s+\\w+\\s*\\(")


def extract_source(text: str) -> str:
    if not isinstance(text, str):
        raise ValueError("source must be text")
    text = text.strip()
    match = BLOCK.fullmatch(text)
    if match:
        text = match.group(1)
    if not text or len(text.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise ValueError("source is empty or exceeds 8192 UTF-8 bytes")
    if FORBIDDEN.search(text) or len(FN.findall(text)) != 1 or not REQUIRED.search(text):
        raise ValueError("expected exactly one fn solve(x: i64) -> i64, with no import/print/main")
    if "```" in text:
        raise ValueError("unexpected Markdown code fence")
    return text + "\n"


def build_prompt(task: str, condition: str) -> str:
    if task not in CASES or condition not in ("baseline", "spec", "examples"):
        raise ValueError("unknown task or condition")
    intro = (
        "Write a complete Cerune function with this exact signature: "
        "fn solve(x: i64) -> i64.\n"
        "No top-level statements, imports, main, or print. Output only Cerune code.\n"
    )
    if condition != "baseline":
        intro += "Language reference:\n" + SPEC + "\n"
    if condition == "examples":
        intro += "Worked example:\n" + EXAMPLE + "\n"
    return intro + "Task: " + CASES[task]["request"] + "\n"


def grade_source(binary: Path, task: str, source: str, timeout: int = 3) -> dict:
    """Executes Cerune code. This is NOT a sandbox: caller must isolate the process."""
    if task not in CASES:
        raise ValueError("unknown task")
    source = extract_source(source)
    binary = binary.resolve(strict=True)
    total = len(CASES[task]["tests"])
    passed = 0
    diagnostics = []
    with tempfile.TemporaryDirectory(prefix="cerune-llm-") as tmp:
        path = Path(tmp) / "candidate.ceru"
        for x, expected in CASES[task]["tests"]:
            path.write_text(source + f"print(solve({x}));\n", encoding="utf-8")
            try:
                # Both passes run in the isolated temporary working directory.
                check = subprocess.run(
                    [str(binary), "check", str(path)], cwd=tmp,
                    stdin=subprocess.DEVNULL, capture_output=True,
                    timeout=timeout, check=False,
                )
                if check.returncode != 0:
                    diagnostics.append({"input": x, "phase": "check", "status": check.returncode})
                    break
                result = subprocess.run(
                    [str(binary), "run", str(path)], cwd=tmp,
                    stdin=subprocess.DEVNULL, capture_output=True,
                    timeout=timeout, check=False,
                )
            except subprocess.TimeoutExpired:
                diagnostics.append({"input": x, "phase": "timeout"})
                break
            except OSError:
                diagnostics.append({"input": x, "phase": "launch-error"})
                break
            valid = result.returncode == 0 and not result.stderr and result.stdout == f"{expected}\n".encode()
            if valid:
                passed += 1
            else:
                diagnostics.append({"input": x, "phase": "wrong-result", "status": result.returncode})
    return {
        "task": task,
        "passed": passed,
        "total": total,
        "score": passed / total,
        "all_pass": passed == total,
        "diagnostics": diagnostics[:3],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", choices=sorted(CASES), required=True)
    parser.add_argument("--condition", choices=("baseline", "spec", "examples"), default="spec")
    parser.add_argument("--print-prompt", action="store_true")
    parser.add_argument("--source", type=Path, help="Model output stored as UTF-8 text")
    parser.add_argument("--binary", type=Path, help="Built Cerune CLI executable")
    parser.add_argument("--timeout", type=int, default=3)
    parser.add_argument("--allow-execution", action="store_true",
                        help="I am running this in an isolated container with no secrets/network")
    args = parser.parse_args(argv)
    if args.print_prompt:
        print(build_prompt(args.task, args.condition))
        return 0
    if not args.source or not args.binary:
        parser.error("--source and --binary required unless --print-prompt")
    if not args.allow_execution:
        parser.error("refusing to run model output without --allow-execution; use an isolated container")
    if not 1 <= args.timeout <= 30:
        parser.error("--timeout must be 1..30 seconds")
    text = args.source.read_text(encoding="utf-8")
    try:
        result = grade_source(args.binary, args.task, text, args.timeout)
    except (ValueError, FileNotFoundError) as e:
        result = {"task": args.task, "passed": 0, "total": len(CASES[args.task]["tests"]),
                  "score": 0.0, "all_pass": False, "diagnostics": [{"phase": "invalid-input", "reason": str(e)}]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
