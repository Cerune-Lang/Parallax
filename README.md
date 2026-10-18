# Parallax

日本語 | [English](README.en.md)

Parallax は、[Cerune](https://github.com/Cerune-Lang/Cerune) の異なる実行経路が一致するかを確かめる公式の差分検証プロジェクトです。

## 目的

- `run`（IR）、`run-mir`（MIR）、`run-vm`（VM）で同じソースの出力を比較する。
- 終了ステータスと標準出力を検証し、不整合を検出する。
- 将来的にネイティブ生成コード比較、ファジング、Cerune本体のCIへの連携を増やす。

## 実行

Cerune CLI と Python 3 が必要です。

```sh
python3 scripts/differential.py --binary /path/to/cerune --cases cases
```

`cases/` 内の `.ceru` と同名の `.expected` に書いた期待標準出力を比較します。GitHub Actions は Cerune をソースからビルドします。

**現段階の対象は正常終了する小さなケースのみ。** 安全な停止を伴う異常系、エラーメッセージの同値性、生成バックエンドやファジングは未対応です。通過は安全性を証明しません。

投稿は [CONTRIBUTING.md](CONTRIBUTING.md) と [SECURITY.md](SECURITY.md) に従ってください。再現サンプルの研究は [Fracta](https://github.com/Cerune-Lang/Fracta) と分担します。ライセンスは未決定です。
