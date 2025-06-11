# stockvalue-exporter

[Link to README in English (README.md)](./README.md)

stockvalue-exporter は Prometheus のカスタムエクスポーターで、株価情報を取得するためのツールです。

## 主な特徴

- Prometheus と統合して株価情報を監視可能。
- Docker を使用して簡単にデプロイと実行ができます。
- yfinance ライブラリを使用して株価情報を取得。

## 技術スタック

このプロジェクトは主に Python と Docker を使用しています。
株価情報の取得には yfinance ライブラリが使用されています。

## インストール方法

Docker イメージを pull するだけで簡単に始められます。

```sh
docker pull mizucopo/stockvalue-exporter:latest
```

## 使い方

以下のコマンドで stockvalue-exporter の Docker コンテナを起動します。

```sh
docker run -v config.json:/app/config.json -p 9100:9100 mizucopo/stockvalue-exporter:latest
```

## 貢献方法

このプロジェクトへの貢献に興味がある方は、プルリクエストを送るか、または issue を開いて議論を始めてください。

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は[LICENSEファイル](/LICENSE)をご参照ください。

## ドキュメンテーション

このREADMEファイルがプロジェクトのドキュメンテーションを兼ねています。

## 連絡先

質問やサポートが必要な場合は、X ([@mizu_copo](https://twitter.com/mizu_copo)) でお気軽にお問い合わせください。
