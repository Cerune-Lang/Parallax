# Control-flow differential testing / 条件分岐・短絡評価

`scripts/control_flow.py` uses deterministic seeds and a small, well-typed grammar to generate `if/else` programs containing comparisons, `!`, `&&` and `||`. Integer expressions may trap. The independent Python oracle evaluates operands in order and skips the right-hand expression for short-circuit cases.

```sh
python3 scripts/control_flow.py --binary /path/to/cerune --seed 1337 --count 24 --depth 2
```

- The program emits `entered` before evaluating the condition. Normal paths print `then` or `else`, followed by `end`.
- Traps preserve `entered\n` as prior stdout and identify the error code.
- Findings are local only under `.parallax-findings/flow`; do not publish unpatched security details.
- Shrinking simplifies boolean subtrees while preserving the coarse discrepancy signature and expected failure classification.
- Bounded depth, case count, per-route timeout and reduction budget keep campaigns small.

日本語: 「実行すべきでない右辺」を評価していないか、分岐結果や実行時診断が3経路で一致するかを確認します。これはカバレッジ誘導型のファジングや安全性の証明ではありません。
