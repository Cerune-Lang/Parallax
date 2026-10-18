#!/usr/bin/env python3
"""Deterministic, bounded expression-tree differential testing for Cerune.

Generates only signed i32 arithmetic in a closed template. All findings stay
local and must be reviewed before any public disclosure.
"""
import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import random
import sys

from seeded import (
    EDGES, MAX_I32, MIN_I32, OPS, assess, load_seeds, simpler_values,
)


@dataclass(frozen=True)
class Leaf:
    value: int


@dataclass(frozen=True)
class Binary:
    op: str
    left: "Expr"
    right: "Expr"


Expr = Leaf | Binary


class Trap(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def evaluate(expr):
    """Check every intermediate operation in left-to-right evaluation order."""
    if isinstance(expr, Leaf):
        return expr.value
    a = evaluate(expr.left)
    b = evaluate(expr.right)
    if expr.op == "+":
        value = a + b
    elif expr.op == "-":
        value = a - b
    elif expr.op == "*":
        value = a * b
    elif expr.op == "/":
        if b == 0:
            raise Trap("division-by-zero")
        if a == MIN_I32 and b == -1:
            raise Trap("division-overflow")
        quotient = abs(a) // abs(b)
        value = -quotient if (a < 0) != (b < 0) else quotient
    else:
        raise ValueError(f"unknown operation: {expr.op}")
    if value < MIN_I32 or value > MAX_I32:
        raise Trap("integer-overflow")
    return value


def render(expr, next_index=0):
    """Return (source expression, declarations, next variable index)."""
    if isinstance(expr, Leaf):
        if not MIN_I32 <= expr.value <= MAX_I32:
            raise ValueError("invalid i32 literal")
        name = f"v{next_index}"
        return name, [f"{name}: i32 = {expr.value};"], next_index + 1
    if expr.op not in OPS:
        raise ValueError("unrecognized operator")
    lhs, declarations, next_index = render(expr.left, next_index)
    rhs, more, next_index = render(expr.right, next_index)
    return f"({lhs} {expr.op} {rhs})", declarations + more, next_index


@dataclass(frozen=True)
class ExpressionCase:
    tree: Expr

    def source(self):
        expression, declarations, _ = render(self.tree)
        return "\n".join([*declarations, f"print({expression});", ""])

    def oracle(self):
        try:
            return {"kind": "success", "stdout": f"{evaluate(self.tree)}\n"}
        except Trap as error:
            return {"kind": "failure", "code": error.code, "stdout": ""}


def generate(seed, count, depth):
    rng = random.Random(seed)

    def make(remaining, force_binary=False):
        if remaining == 0 or (not force_binary and rng.randrange(4) == 0):
            value = rng.choice(EDGES) if rng.randrange(4) else rng.randint(-100, 100)
            return Leaf(value)
        return Binary(rng.choice(OPS), make(remaining - 1), make(remaining - 1))

    for _ in range(count):
        yield ExpressionCase(make(rng.randint(1, depth), force_binary=True))


def paths(tree, path=()):
    yield path, tree
    if isinstance(tree, Binary):
        yield from paths(tree.left, path + (0,))
        yield from paths(tree.right, path + (1,))


def replace(tree, path, replacement):
    if not path:
        return replacement
    if not isinstance(tree, Binary):
        raise ValueError("path is not present in expression")
    if path[0] == 0:
        return Binary(tree.op, replace(tree.left, path[1:], replacement), tree.right)
    return Binary(tree.op, tree.left, replace(tree.right, path[1:], replacement))


def size(case):
    all_nodes = list(paths(case.tree))
    total_magnitude = sum(abs(node.value) for _, node in all_nodes if isinstance(node, Leaf))
    return (len(all_nodes), len(case.source()), total_magnitude)


def shrink_candidates(case):
    proposals = set()
    for path, node in paths(case.tree):
        if isinstance(node, Binary):
            replacements = (node.left, node.right, Leaf(0), Leaf(1), Leaf(-1))
        else:
            replacements = tuple(Leaf(value) for value in simpler_values(node.value))
        for candidate in replacements:
            proposed = ExpressionCase(replace(case.tree, path, candidate))
            if size(proposed) < size(case):
                proposals.add(proposed)
    return sorted(proposals, key=lambda candidate: (size(candidate), candidate.source()))


def minimize(case, fingerprint, probe, budget=64):
    """Keep the failure category and its independent oracle classification."""
    current = case
    classification = current.oracle()
    attempts = 0
    while attempts < budget:
        changed = False
        for candidate in shrink_candidates(current):
            if attempts >= budget:
                break
            if (candidate.oracle().get("kind"), candidate.oracle().get("code")) != (
                classification.get("kind"), classification.get("code")
            ):
                continue
            attempts += 1
            if probe(candidate) == fingerprint:
                current = candidate
                changed = True
                break
        if not changed:
            break
    return current, attempts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, default=Path("corpus/seeds.json"))
    parser.add_argument("--seed", type=int, action="append")
    parser.add_argument("--count", type=int, default=16)
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=3)
    parser.add_argument("--budget", type=int, default=64)
    parser.add_argument("--out-dir", type=Path, default=Path(".parallax-findings/expressions"))
    args = parser.parse_args(argv)
    if not (1 <= args.count <= 1000 and 1 <= args.depth <= 4 and
            1 <= args.timeout <= 60 and 0 <= args.budget <= 200):
        parser.error("expected count 1..1000, depth 1..4, timeout 1..60 and budget 0..200")
    if args.seed and any(seed < 0 for seed in args.seed):
        parser.error("seeds must be nonnegative")
    seeds = args.seed if args.seed is not None else load_seeds(args.corpus)
    binary = args.binary.resolve()
    if not binary.is_file():
        parser.error("binary does not exist")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    scratch = args.out_dir / "current.ceru"
    failures = 0
    checked = 0
    try:
        for seed in seeds:
            for index, case in enumerate(generate(seed, args.count, args.depth)):
                checked += 1
                fingerprint = assess(case, binary, scratch, args.timeout)
                if not fingerprint:
                    continue
                failures += 1
                small, attempts = minimize(
                    case, fingerprint,
                    lambda candidate: assess(candidate, binary, scratch, args.timeout),
                    args.budget,
                )
                folder = args.out_dir / f"finding-{failures:04d}"
                folder.mkdir(exist_ok=False)
                (folder / "original.ceru").write_text(case.source(), encoding="utf-8")
                (folder / "minimized.ceru").write_text(small.source(), encoding="utf-8")
                (folder / "metadata.json").write_text(json.dumps({
                    "seed": seed, "case_index": index, "fingerprint": fingerprint,
                    "original_oracle": case.oracle(), "minimized_oracle": small.oracle(),
                    "reduction_probes": attempts
                }, indent=2) + "\n", encoding="utf-8")
                print(f"Potential discrepancy retained locally in {folder}; review privately.", file=sys.stderr)
    finally:
        scratch.unlink(missing_ok=True)
    print(f"Checked {checked} expression trees; findings: {failures}")
    return int(failures != 0)


if __name__ == "__main__":
    sys.exit(main())
