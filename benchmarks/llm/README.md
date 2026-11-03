# Cerune Language Acquisition Benchmark — pilot v1

[Parallax](../../README.md)のLLM評価実験です。Ceruneをほぼ知らないモデルが、渡された言語仕様から構文・実行意味を理解できるかを調べます。**初版はパイロットであり、正式な研究結果やモデルの優劣を断定するものではありません。**

## 何を比較するか

| 条件 | 与える情報 | 評価 |
| --- | --- | --- |
| `baseline` | Ceruneのコードと問題文だけ | 事前知識・推測による正答 |
| `spec` | 上記に最小限の言語仕様を追加 | 仕様書による適応 |
| `examples` | 同じ仕様に、評価ケースとは別の短い例を追加 | 少数例による適応 |

同じモデル／同じケース／同じ採点で比較します。Kaggleタスクは各ケースを独立したchatで実行し、スコアは0.0～1.0の正答率です。条件を実行する順序やモデルの応答が残らないよう、同じ会話を使い回しません。

## Phase 1: Kaggle Community Benchmarks（安全な出力予測）

`kaggle_task.py`に、Kaggleの`@kbench.task`で次の3タスクを用意しています。

- `cerune-output-baseline-v1`
- `cerune-output-spec-v1`
- `cerune-output-examples-v1`

対象は算術、配列とfor、whileと整数除算の3ケース。**モデルに生成コードを実行させず、出力の整数を予測させます。** すべての正解・出題内容は公開されるため、これは評価手順を検証するパイロットです。モデル汚染への耐性、未知性の厳密な保証、統計的な有意差は主張しません。

[Kaggle公式ドキュメント](https://www.kaggle.com/docs/benchmarks)と[公式Pythonライブラリ](https://github.com/Kaggle/kaggle-benchmarks)に従い、Kaggleのタスクエディタにスクリプトを貼るか、対応するKaggle CLIで次のように登録します（モデル推論の実行には利用者のKaggleアカウントが必要）。

```sh
kaggle benchmarks init
kaggle benchmarks tasks push cerune-output-baseline-v1 -f benchmarks/llm/kaggle_task.py
kaggle benchmarks tasks push cerune-output-spec-v1 -f benchmarks/llm/kaggle_task.py
kaggle benchmarks tasks push cerune-output-examples-v1 -f benchmarks/llm/kaggle_task.py
```

KaggleタスクのブラウザUIで実行する場合、`cerune_output_baseline.run(llm=kbench.llm)`などを呼びます。利用可能なモデルはKaggle内の`list(kbench.llms.keys())`で確認してください。**このPRではKaggleにタスク登録・モデル実行はしていません。**

## Phase 2: Cerune実行によるコード生成採点（ローカル）

`codegen_eval.py`は、モデルが生成した`fn solve(x: i64) -> i64`を受け取り、異なる入力で実際にCeruneを起動して採点します。題材は`abs`、`clamp`、`sum_squares`。

仕様書ありのプロンプト例：

```sh
python3 benchmarks/llm/codegen_eval.py --task clamp --condition spec --print-prompt
```

モデルの回答をテキストファイルに保存したら、**ネットワーク・秘密情報から隔離したコンテナ内のみ**で実行します：

```sh
python3 benchmarks/llm/codegen_eval.py \
  --task clamp --source candidate.txt --binary /path/to/cerune \
  --allow-execution
```

`--allow-execution`は誤操作防止の確認であり、**安全なsandboxを実装するものではありません**。外部提供のコードを通常の開発PCやKaggleノートブックへ無条件に流さないでください。コンテナのネットワーク・権限・資源上限は実行者が別途設定します。入力コードのサイズ、関数シグネチャ、import/print/main等を制限し、Ceruneプロセスにはタイムアウトを設けます。これらだけでは悪意ある入力に対する完全な隔離にはなりません。

正答判定は各入力のstdout、終了コード、stderrで行います。問題文にはテスト入力を示しません。現状のパイロットでは検査データもリポジトリ公開なので本格的な隠しテストではなく、今後は別のプライベートデータセットと既知・未知ケースの分離が必要です。

### 検証（実モデルなし）

```sh
python3 -m unittest discover -s tests -p 'test_llm_benchmark.py' -v
```

CIでは別途、Ceruneで既知の正解コード3件をコンパイル・実行して採点器の整合性を確認します。

## 研究上の注意

- 仕様書のスナップショットとCeruneのコミットSHAを記録して、言語の変更から比較を守る。
- モデル・バージョン、設定温度、実行日、回答テキスト、ケースID、条件、入力トークン量を記録する。
- 小さなパイロットの平均正答率だけでモデル順位を主張しない。入力を入れ替えた反復と信頼区間が必要。
- `spec`と`examples`はプロンプト長が異なるため、改善に対して「例の効果」と「トークン量の効果」を区別する。
- 公開されたCerune仕様をモデルが事前に学んだ可能性を排除できない。厳密な未知言語能力には人工的に変えた構文・非公開評価データ・事前汚染検査を追加する。
- 正解コードをPythonで算出する独立オラクルとCerune実行を比較し、生成したコードを自己採点させない。

**範囲外:** 自作LLM重みの評価、Ceruneコンパイラの正しさの証明、Kaggleアカウントへの自動公開。
