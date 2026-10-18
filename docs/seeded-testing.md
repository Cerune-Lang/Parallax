# Seeded differential testing / シード付き差分検証

日本語: `scripts/seeded.py` は固定したシードから、i32の加減乗除プログラムを生成します。生成対象は小さな閉じた式テンプレートであり、ファイルI/Oやネットワーク操作を生成しません。Python側で期待値・実行時診断コードを独立に計算し、Ceruneの IR / MIR / VM 経路を比較します。

```sh
python3 scripts/seeded.py --binary /path/to/cerune --corpus corpus/seeds.json --count 24
python3 scripts/seeded.py --binary /path/to/cerune --seed 1337 --count 5 --budget 20
```

- `--count`: seedごとの生成件数。定期CIの標準値は小さく抑えます。
- `--timeout`: 各経路の最大実行秒数。
- `--budget`: 1件の失敗を縮小する最大検証回数。
- Findings are stored locally in `.parallax-findings/`, excluded by `.gitignore`.
- Do not upload or publish findings automatically. Privately investigate discrepancies first, then coordinate disclosure under `SECURITY.md`.

The reducer is intentionally limited: it simplifies numeric operands only while preserving its **coarse failure classification**; it does not guarantee the same root cause. This is an initial deterministic generator, not coverage-guided fuzzing or a security proof.

English: Small bounded deterministic i32 arithmetic campaigns compare IR, MIR, and VM against an independent Python arithmetic oracle. Any discrepancies must be triaged privately; minimization is best-effort.
