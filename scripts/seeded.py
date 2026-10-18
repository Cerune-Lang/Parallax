#!/usr/bin/env python3
"""Deterministic, bounded, local differential testing of Cerune i32 operations.

Only generates a fixed arithmetic template; no arbitrary source or network access.
Findings remain on disk rather than in public CI artifacts.
"""
import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import random
import subprocess
import sys

from differential import ROUTES, compare_result, DIAGNOSTIC

MIN_I32 = -(2 ** 31)
MAX_I32 = 2 ** 31 - 1
OPS = ('+', '-', '*', '/')
EDGES = (MIN_I32, MIN_I32 + 1, -1024, -2, -1, 0, 1, 2, 1024, MAX_I32 - 1, MAX_I32)


@dataclass(frozen=True)
class Case:
    left: int
    op: str
    right: int

    def source(self):
        assert self.op in OPS
        assert MIN_I32 <= self.left <= MAX_I32
        assert MIN_I32 <= self.right <= MAX_I32
        return f'left: i32 = {self.left};\nright: i32 = {self.right};\nprint(left {self.op} right);\n'

    def oracle(self):
        a, b = self.left, self.right
        if self.op == '+':
            result = a + b
        elif self.op == '-':
            result = a - b
        elif self.op == '*':
            result = a * b
        elif self.op == '/':
            if b == 0:
                return {'kind': 'failure', 'code': 'division-by-zero', 'stdout': ''}
            if a == MIN_I32 and b == -1:
                return {'kind': 'failure', 'code': 'division-overflow', 'stdout': ''}
            quotient = abs(a) // abs(b)
            result = -quotient if (a < 0) != (b < 0) else quotient
        else:
            raise ValueError('unsupported operation')
        if result < MIN_I32 or result > MAX_I32:
            return {'kind': 'failure', 'code': 'integer-overflow', 'stdout': ''}
        return {'kind': 'success', 'stdout': f'{result}\n'}


def generate(seed, count):
    rng = random.Random(seed)
    for _ in range(count):
        def operand():
            return rng.choice(EDGES) if rng.randrange(3) else rng.randint(-1000, 1000)
        yield Case(operand(), rng.choice(OPS), operand())


def run_one(binary, source, route, timeout):
    try:
        result = subprocess.run(
            [str(binary), route, str(source), '--diagnostic-format', 'runtime-v1'],
            stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired:
        return ('timeout',), None
    except OSError:
        return ('launch-error',), None
    codes = tuple(code.decode('ascii') for code in DIAGNOSTIC.findall(result.stderr))
    status = ('result', result.returncode, result.stdout, codes)
    return status, result


def assess(case, binary, source, timeout):
    source.write_text(case.source(), encoding='utf-8')
    oracle = case.oracle()
    statuses = []
    incorrect = []
    for route in ROUTES:
        status, result = run_one(binary, source, route, timeout)
        statuses.append(status)
        if result is None:
            incorrect.append((route, status[0]))
        elif not compare_result(result, oracle):
            incorrect.append((route, 'oracle-mismatch'))
    if len(set(statuses)) > 1:
        incorrect.append(('routes', 'disagreement'))
    return tuple(incorrect)


def size(case):
    return (len(case.source()), abs(case.left) + abs(case.right), abs(case.left), abs(case.right))


def simpler_values(value):
    options = {0, 1, -1, 2, -2, value // 2, int(value / 2)}
    return sorted((v for v in options if MIN_I32 <= v <= MAX_I32 and v != value), key=lambda x: (abs(x), x))


def minimize(case, fingerprint, probe, budget=48):
    current = case
    attempts = 0
    while attempts < budget:
        proposals = []
        for left in simpler_values(current.left):
            proposals.append(Case(left, current.op, current.right))
        for right in simpler_values(current.right):
            proposals.append(Case(current.left, current.op, right))
        candidates = sorted((x for x in set(proposals) if size(x) < size(current)), key=size)
        changed = False
        for candidate in candidates:
            if attempts >= budget:
                break
            attempts += 1
            if probe(candidate) == fingerprint:
                current = candidate
                changed = True
                break
        if not changed:
            break
    return current, attempts


def load_seeds(path):
    entries = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(entries, list) or not entries:
        raise ValueError('seed corpus must be a non-empty list')
    ids = [entry['id'] for entry in entries]
    seeds = [entry['seed'] for entry in entries]
    if len(set(ids)) != len(ids) or len(set(seeds)) != len(seeds) or any(type(s) is not int or s < 0 for s in seeds):
        raise ValueError('seed IDs and nonnegative numeric seeds must be unique')
    return seeds


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--corpus', type=Path, default=Path('corpus/seeds.json'))
    parser.add_argument('--seed', type=int, action='append', help='Override the curated seed corpus')
    parser.add_argument('--count', type=int, default=24, help='Cases per seed (max 1000)')
    parser.add_argument('--timeout', type=int, default=3, help='Per-route seconds (max 60)')
    parser.add_argument('--budget', type=int, default=48, help='Reduction probes (max 200)')
    parser.add_argument('--out-dir', type=Path, default=Path('.parallax-findings'))
    args = parser.parse_args(argv)
    if not 1 <= args.count <= 1000 or not 1 <= args.timeout <= 60 or not 0 <= args.budget <= 200:
        parser.error('count must be 1..1000, timeout 1..60, budget 0..200')
    if args.seed is not None and any(s < 0 for s in args.seed):
        parser.error('seeds must be nonnegative')
    seeds = args.seed if args.seed is not None else load_seeds(args.corpus)
    binary = args.binary.resolve()
    if not binary.is_file():
        parser.error('binary does not exist')
    args.out_dir.mkdir(parents=True, exist_ok=True)
    scratch = args.out_dir / 'current.ceru'
    total = 0
    findings = 0
    try:
        for seed in seeds:
            for index, case in enumerate(generate(seed, args.count)):
                total += 1
                fingerprint = assess(case, binary, scratch, args.timeout)
                if not fingerprint:
                    continue
                findings += 1
                shrunk, attempts = minimize(
                    case, fingerprint,
                    lambda candidate: assess(candidate, binary, scratch, args.timeout),
                    budget=args.budget,
                )
                dirname = args.out_dir / f'finding-{findings:04d}'
                dirname.mkdir(exist_ok=False)
                (dirname / 'original.ceru').write_text(case.source(), encoding='utf-8')
                (dirname / 'minimized.ceru').write_text(shrunk.source(), encoding='utf-8')
                (dirname / 'metadata.json').write_text(json.dumps({
                    'seed': seed, 'index': index, 'fingerprint': fingerprint,
                    'expected': case.oracle(), 'minimized_expected': shrunk.oracle(),
                    'reduction_probes': attempts,
                }, indent=2) + '\n', encoding='utf-8')
                print(f'Potential discrepancy saved locally in {dirname}; do not publish without review.', file=sys.stderr)
    finally:
        scratch.unlink(missing_ok=True)
    print(f'Checked {total} deterministic cases; findings: {findings}')
    return int(findings > 0)


if __name__ == '__main__':
    sys.exit(main())
