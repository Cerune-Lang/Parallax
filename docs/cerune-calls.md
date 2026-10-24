# Cerune-authored function-call testing / Ceruneによる関数呼び出し検証

`cerune/generate_calls.ceru` emits **16 deterministic bounded call cases**. `scripts/cerune_calls.py` validates its numeric protocol and compares IR, MIR, SSA and VM outputs with an **independent Python oracle**.

```sh
python3 scripts/cerune_calls.py --binary /path/to/cerune --generator cerune/generate_calls.ceru
```

Protocol v1: version `1`, count `16`, followed by `mode`, `a`, `b` for each case. Two cases per mode, operands in -40..40, and both return branches for modes 3 and 6.

| Mode | Tested behavior |
| --- | --- |
| 0 | Direct function call |
| 1 | Nested non-recursive calls |
| 2 | Left-to-right argument evaluation / stdout |
| 3 | Value-returning early return |
| 4 | Copied array passed to and returned from a function |
| 5 | String argument and returned string |
| 6 | Void early return |
| 7 | Runtime failure in the second argument after previous stdout |

The oracle verifies stdout, status and `runtime-v1` diagnostic codes, then checks agreement between all four routes. The Python process handles file I/O, subprocess isolation and independent expected values. **Recursion and C/LLVM/QBE/WAT/Native comparisons are out of scope.** Do not automatically publish suspected security differences; investigate privately under `SECURITY.md`.

日本語: Cerune製の固定seedによる関数呼び出しケースをPythonの独立期待値で検証します。再帰・生成バックエンドは別PRで扱います。
