# Cerune-generated function-boundary tests / 関数境界の配列テスト

`cerune/generate_functions.ceru` deterministically emits **24 cases**, covering fixed `[i64; 3]` and dynamic `[i64]` values crossing function boundaries. A Python reference model independently computes exact stdout and runtime failure codes.

| Mode | What is verified |
| --- | --- |
| 0 | Callee copies and edits an array, then returns it. Caller retains original. |
| 1 | Caller edits a returned array, leaving original untouched. |
| 2 | Nested calls return independent values and preserve output order. |
| 3 | Invalid indexed write inside callee traps before its remaining body. |
| 4 | Left-to-right argument evaluation: second helper traps before callee body. |
| 5 | Successful argument evaluation, entry to callee, and unmodified return. |

```sh
python3 scripts/cerune_functions.py --binary /path/to/cerune --generator cerune/generate_functions.ceru
```

Protocol v1: `1`, case count `24`, then seven numbers per case (array kind, mode, three i64 elements, replacement, index). The host validates ranges before generating test programs. Results for `run`, `run-mir`, and `run-vm` must match the Python model. The Cerune generator does not perform filesystem operations or spawn processes; Python handles those responsibilities and retains an independent oracle.

日本語: 関数引数と返却値を通した配列の独立コピー、評価順序、関数内停止と先行出力を検証します。未確認の差分は公開せず、`SECURITY.md` に従って非公開で調査してください。
