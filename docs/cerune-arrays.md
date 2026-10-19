# Cerune-authored array testing / Ceruneによる配列テスト

`cerune/generate_arrays.ceru` deterministically generates **32 cases** across fixed `[i64; 3]` and dynamic `[i64]` arrays. A Python adapter validates the versioned numeric protocol and computes the independently expected stdout and runtime failure.

The cases cover independent array copies, mutation of the original and copied values, valid and negative/out-of-range reads and writes, and an assignment with a deliberately trapping right-hand side. Index bounds must be checked before evaluating that right-hand side.

```sh
python3 scripts/cerune_arrays.py --binary /path/to/cerune --generator cerune/generate_arrays.ceru
```

Protocol v1: version `1`, count `32`, then seven numbers per case: array kind, mode, first value, second value, third value, replacement and index. Each execution route is verified against independent Python expectations; a mismatch is **not** automatically published as a vulnerability.

日本語: 固定長配列と動的配列の独立コピー、要素更新、範囲外アクセス、停止前の出力を確認する。ケース生成はCerune、実行管理と独立オラクルはPythonに残す。未公開の差分は `SECURITY.md` に従って非公開で調査する。
