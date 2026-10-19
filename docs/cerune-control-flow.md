# Cerune-authored control-flow generation / Ceruneでの条件式生成

The `cerune/generate_flow.ceru` program emits a deterministic, versioned 24-case corpus. Each record contains a nested `&&` / `||` expression, with two boolean guards and an integer comparison. Some comparisons contain an intentionally invalid division, which must **not** execute when either guard short-circuits.

```sh
python3 scripts/cerune_flow.py --binary /path/to/cerune --generator cerune/generate_flow.ceru
```

Protocol v1: line 1 is version `1`, line 2 is count `24`; each case has nine integer fields: outer logical operator, outer guard, inner logical operator, inner guard, comparison operator, arithmetic operator, left operand, right operand, comparison target. Logical operator IDs: 0 = `&&`, 1 = `||`; comparison IDs: 0 = `==`, 1 = `!=`, 2 = `<`, 3 = `<=`, 4 = `>`, 5 = `>=`; arithmetic IDs: 0 = `+`, 1 = `-`, 2 = `*`, 3 = `/`.

Python validates all protocol fields and constructs a typed `FlowCase`. Its independent evaluator computes the expected branch, prior output, or exact runtime failure category before comparing IR/MIR/VM. This does **not** move the independent oracle or subprocess management to Cerune. No unreviewed findings are uploaded.

日本語: Ceruneで短絡評価用データを生成し、Pythonの独立した期待値計算器で分岐・停止理由・先行出力を検証します。未公開の不整合は公開せず、`SECURITY.md` に従って非公開で調査してください。
