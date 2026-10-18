# Expression-tree differential testing / 式木の差分テスト

`scripts/expressions.py` adds bounded arithmetic expression trees to Parallax.

- Seeded deterministic generation of nested i32 `+`, `-`, `*` and `/` expressions.
- A Python reference evaluator checks **every intermediate operation** (including left-to-right trap order).
- Same IR / MIR / VM checks as `seeded.py`, with structured runtime diagnostics.
- Reduction replaces subexpressions with smaller subtrees or literals, retaining the coarse mismatch fingerprint and oracle outcome category.
- Unreviewed findings are written only to ignored local `.parallax-findings/expressions`, never uploaded by CI.

```sh
python3 scripts/expressions.py --binary /path/to/cerune --seed 1337 --count 30 --depth 3
```

Depth is deliberately capped at 4 and executions are time-limited. CI starts with a very small bounded run. This is not coverage-guided fuzzing, not a proof of security, and not a guarantee that minimized mismatches share an identical root cause.

日本語: 固定シードから深さ制限付きの計算式を生成し、各中間演算の値・エラーをPython側で独立判定します。未公開の不整合が見つかったら公開Issueに貼らず、`SECURITY.md` に従って非公開で調査してください。
