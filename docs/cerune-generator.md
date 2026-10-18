# Cerune generator experiment

This first dogfooding experiment uses a Cerune program to produce deterministic arithmetic triples on stdout. Python remains responsible for process isolation, interpreting the protocol and independently computing expected arithmetic results. It does not replace the existing generator yet.

```sh
cerune run cerune/generate.ceru
```

Output is three decimal lines per case (left operand, operation ID, right operand), 12 cases total. Operations 0..3 correspond to addition, subtraction, multiplication and division. The LCG has a fixed seed and bounded i64 intermediate values. The experiment does not attempt file writes or subprocess execution from Cerune.

日本語: Cerune本体でシードから数値を生成する最初のdogfooding実験です。現状は出力プロトコルを確認する段階で、既存Python製ファザーは置き換えません。
