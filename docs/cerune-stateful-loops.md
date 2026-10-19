# Cerune-authored stateful loop testing / Ceruneによる状態遷移テスト

`cerune/generate_loops.ceru` deterministically emits **30 typed, bounded loop specifications** without host filesystem or subprocess APIs. `scripts/cerune_loops.py` validates this protocol, emits test programs with mutable `i32` variables, and independently computes every intermediate value and stdout line in Python. It then compares the expected result with Cerune's IR, MIR and VM execution routes.

## Supported transition modes

- `0`: checked addition in a `while` loop
- `1`: checked multiplication
- `2`: `continue` skips even iterations but still advances the index
- `3`: `break` before updating at the chosen iteration
- `4`: alternating addition and multiplication

The fixed corpus includes zero iterations, an overflow with partial stdout, finite loops, `continue`, `break`, and state traces. Runtime failures are not treated as successes merely because the process exits nonzero: the harness checks the exact structured diagnostic code, status and prior stdout.

```sh
python3 scripts/cerune_loops.py --binary /path/to/cerune --generator cerune/generate_loops.ceru
```

Protocol v1: `1` followed by `30`, then five decimal lines per case: mode, starting `i32`, step `i32`, rounds `i64` (0–8), stop `i64` (1–9).

The independent Python oracle and process isolation remain intentionally outside Cerune. Cases are deterministic, not coverage-guided fuzzing. A discrepancy should be investigated privately according to `SECURITY.md`; never automatically publish unpatched findings.

日本語: 可変変数の更新、反復回数、`continue`・`break`、途中までの標準出力と算術停止を比較します。Pythonの独立オラクルとプロセス管理を維持しつつ、Ceruneが生成するケースの範囲を広げるdogfoodingです。
