# Cerune-authored nested test generation / Cerune製の入れ子式生成

`cerune/generate_nested.ceru` uses a fixed seed and bounded arithmetic to emit **16 nested i32 arithmetic expressions** as a versioned line protocol. Every fourth case explicitly exercises overflow or division by zero; the rest include ordinary arithmetic values.

The Python adapter `scripts/cerune_nested.py` validates the protocol, constructs the nested expression using the existing `ExpressionCase`, and checks IR/MIR/VM against its **independent Python oracle**.

```sh
python3 scripts/cerune_nested.py --binary /path/to/cerune --generator cerune/generate_nested.ceru
```

Protocol v1: first line `1`, second line `16`, then five decimal lines per case: left operand, right operand, tail operand, inner operation ID and outer operation ID. IDs are 0:+, 1:-, 2:*, 3:/, representing `((left op right) op tail)`.

**Boundaries:** This uses a fixed seed rather than accepting CLI arguments in Cerune. The Python host still handles temporary files, subprocesses and test orchestration. No findings are automatically published. This is dogfooding, not complete migration of the test harness.

日本語: Cerune自身で入れ子式の数値と演算子を生成し、Pythonの独立した期待値計算器で検証します。ファイル操作やプロセス起動は引き続きPythonが担当します。意図しない差分が出た場合は公開前に非公開で調査してください。
