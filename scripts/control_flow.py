#!/usr/bin/env python3
"""Bounded deterministic control-flow and short-circuit differential testing.

All inputs are locally generated from a fixed, typed grammar. Potential
discrepancies are saved locally and must be reviewed before disclosure.
"""
import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import random
import sys

from expressions import Binary, Leaf, Trap, evaluate as eval_integer, render as render_integer
from seeded import EDGES, assess, load_seeds, simpler_values


@dataclass(frozen=True)
class BoolLiteral:
    value: bool


@dataclass(frozen=True)
class Comparison:
    op: str
    left: object
    right: object


@dataclass(frozen=True)
class Logical:
    op: str
    left: object
    right: object


@dataclass(frozen=True)
class Negation:
    operand: object


COMPARISONS = ("==", "!=", "<", "<=", ">", ">=")
LOGICALS = ("&&", "||")


def eval_bool(expr):
    if isinstance(expr, BoolLiteral):
        return expr.value
    if isinstance(expr, Comparison):
        a = eval_integer(expr.left)
        b = eval_integer(expr.right)
        if expr.op == "==":
            return a == b
        if expr.op == "!=":
            return a != b
        if expr.op == "<":
            return a < b
        if expr.op == "<=":
            return a <= b
        if expr.op == ">":
            return a > b
        if expr.op == ">=":
            return a >= b
        raise ValueError("unsupported comparison")
    if isinstance(expr, Negation):
        return not eval_bool(expr.operand)
    if isinstance(expr, Logical):
        left = eval_bool(expr.left)
        if expr.op == "&&":
            return left and eval_bool(expr.right)
        if expr.op == "||":
            return left or eval_bool(expr.right)
        raise ValueError("unsupported logical operator")
    raise TypeError("unsupported boolean node")


def render_bool(expr, next_index=0):
    if isinstance(expr, BoolLiteral):
        return ("true" if expr.value else "false"), [], next_index
    if isinstance(expr, Comparison):
        if expr.op not in COMPARISONS:
            raise ValueError("invalid comparison operator")
        left, declarations, next_index = render_integer(expr.left, next_index)
        right, rest, next_index = render_integer(expr.right, next_index)
        return f"({left} {expr.op} {right})", declarations + rest, next_index
    if isinstance(expr, Negation):
        inside, declarations, next_index = render_bool(expr.operand, next_index)
        return f"(!{inside})", declarations, next_index
    if isinstance(expr, Logical):
        if expr.op not in LOGICALS:
            raise ValueError("invalid logical operator")
        left, declarations, next_index = render_bool(expr.left, next_index)
        right, rest, next_index = render_bool(expr.right, next_index)
        return f"({left} {expr.op} {right})", declarations + rest, next_index
    raise TypeError("unsupported boolean node")


@dataclass(frozen=True)
class FlowCase:
    condition: object

    def source(self):
        condition, declarations, _ = render_bool(self.condition)
        return "\n".join([
            *declarations,
            'print("entered");',
            f"if {condition} {{",
            '    print("then");',
            "} else {",
            '    print("else");',
            "}",
            'print("end");',
            "",
        ])

    def oracle(self):
        stdout = "entered\n"
        try:
            branch = "then" if eval_bool(self.condition) else "else"
        except Trap as error:
            return {"kind": "failure", "code": error.code, "stdout": stdout}
        return {"kind": "success", "stdout": stdout + branch + "\nend\n"}


def make_bad_predicate():
    return Comparison("==", Binary("/", Leaf(1), Leaf(0)), Leaf(0))


def generate(seed, count, depth):
    rng = random.Random(seed)

    def make_integer():
        def leaf():
            return Leaf(rng.choice(EDGES) if rng.randrange(4) else rng.randint(-20, 20))
        if rng.randrange(4) == 0:
            return Binary(rng.choice(("+", "-", "*", "/")), leaf(), leaf())
        return leaf()

    def make_bool(level):
        if level <= 0 or rng.randrange(4) == 0:
            if rng.randrange(4) == 0:
                return BoolLiteral(bool(rng.randrange(2)))
            return Comparison(rng.choice(COMPARISONS), make_integer(), make_integer())
        if rng.randrange(5) == 0:
            return Negation(make_bool(level - 1))
        return Logical(rng.choice(LOGICALS), make_bool(level - 1), make_bool(level - 1))

    for index in range(count):
        if index % 4 == 0:
            op = rng.choice(LOGICALS)
            left_value = rng.choice((False, True))
            condition = Logical(op, BoolLiteral(left_value), make_bad_predicate())
        elif index % 4 == 1:
            op = rng.choice(LOGICALS)
            left_value = rng.choice((False, True))
            condition = Logical(op, BoolLiteral(left_value), make_bool(depth - 1))
        else:
            condition = make_bool(depth)
        yield FlowCase(condition)


def bool_paths(tree, path=()):
    yield path, tree
    if isinstance(tree, Logical):
        yield from bool_paths(tree.left, path + (0,))
        yield from bool_paths(tree.right, path + (1,))
    elif isinstance(tree, Negation):
        yield from bool_paths(tree.operand, path + (0,))


def replace_bool(tree, path, replacement):
    if not path:
        return replacement
    if isinstance(tree, Logical):
        if path[0] == 0:
            return Logical(tree.op, replace_bool(tree.left, path[1:], replacement), tree.right)
        return Logical(tree.op, tree.left, replace_bool(tree.right, path[1:], replacement))
    if isinstance(tree, Negation) and path[0] == 0:
        return Negation(replace_bool(tree.operand, path[1:], replacement))
    raise ValueError("invalid boolean subtree path")


def shrink_candidates(case):
    candidates = set()
    for path, node in bool_paths(case.condition):
        replacements = [BoolLiteral(False), BoolLiteral(True)]
        if isinstance(node, Logical):
            replacements += [node.left, node.right]
        elif isinstance(node, Negation):
            replacements += [node.operand]
        elif isinstance(node, Comparison):
            # Simplify a comparison into a literal for coarse reduction.
            replacements += [BoolLiteral(node.op == "==")]
        for replacement in replacements:
            candidate = FlowCase(replace_bool(case.condition, path, replacement))
            if len(candidate.source()) < len(case.source()):
                candidates.add(candidate)
    return sorted(candidates, key=lambda c: (len(c.source()), c.source()))


def minimize(case, fingerprint, probe, budget=48):
    original = (case.oracle().get("kind"), case.oracle().get("code"))
    current, attempts = case, 0
    while attempts < budget:
        changed = False
        for candidate in shrink_candidates(current):
            if attempts >= budget:
                break
            if (candidate.oracle().get("kind"), candidate.oracle().get("code")) != original:
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
    parser.add_argument("--count", type=int, default=12)
    parser.add_argument("--depth", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=3)
    parser.add_argument("--budget", type=int, default=48)
    parser.add_argument("--out-dir", type=Path, default=Path(".parallax-findings/flow"))
    args = parser.parse_args(argv)
    if not (1 <= args.count <= 1000 and 1 <= args.depth <= 3 and
            1 <= args.timeout <= 60 and 0 <= args.budget <= 200):
        parser.error("count 1..1000, depth 1..3, timeout 1..60, budget 0..200 required")
    if args.seed and any(seed < 0 for seed in args.seed):
        parser.error("seeds must be nonnegative")
    seeds = args.seed if args.seed is not None else load_seeds(args.corpus)
    binary = args.binary.resolve()
    if not binary.is_file():
        parser.error("binary does not exist")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    scratch = args.out_dir / "current.ceru"
    count, findings = 0, 0
    try:
        for seed in seeds:
            for index, case in enumerate(generate(seed, args.count, args.depth)):
                count += 1
                fingerprint = assess(case, binary, scratch, args.timeout)
                if not fingerprint:
                    continue
                findings += 1
                small, attempts = minimize(
                    case, fingerprint,
                    lambda candidate: assess(candidate, binary, scratch, args.timeout),
                    args.budget,
                )
                folder = args.out_dir / f"finding-{findings:04d}"
                folder.mkdir(exist_ok=False)
                (folder / "original.ceru").write_text(case.source(), encoding="utf-8")
                (folder / "minimized.ceru").write_text(small.source(), encoding="utf-8")
                (folder / "metadata.json").write_text(json.dumps({
                    "seed": seed, "index": index, "fingerprint": fingerprint,
                    "oracle": case.oracle(), "minimized_oracle": small.oracle(),
                    "reduction_probes": attempts,
                }, indent=2) + "\n", encoding="utf-8")
                print(f"Possible discrepancy retained locally in {folder}; investigate privately.", file=sys.stderr)
    finally:
        scratch.unlink(missing_ok=True)
    print(f"Checked {count} branching cases; findings: {findings}")
    return int(findings > 0)


if __name__ == "__main__":
    sys.exit(main())
