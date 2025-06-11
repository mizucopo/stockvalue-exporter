# CLAUDE.md

このファイルは、このリポジトリでコードを扱う際の Claude Code (claude.ai/code) へのガイダンスを提供します。

## プロジェクト概要

Python と Flask を使用して構築された株価監視用の Prometheus カスタムエクスポーターです。Yahoo Finance API から株価データを取得し、Prometheus メトリクスとして公開します。

## アーキテクチャ

- **メインアプリケーション**: `app/main.py` - Prometheus メトリクスエンドポイントを持つ Flask ウェブサーバー
- **パッケージ管理**: `pyproject.toml` 設定での `uv` パッケージマネージャーを使用
- **コンテナ化**: 開発・本番環境向けマルチステージ Docker ビルド
- **データソース**: `yfinance` ライブラリ経由の Yahoo Finance API
- **メトリクス**: 株価、出来高、時価総額、PER、エラー追跡を含む Prometheus メトリクス

## 開発コマンド

### パッケージ管理
```bash
cd app
uv sync --dev        # 開発ツールを含む依存関係をインストール
uv sync --no-dev     # 本番環境の依存関係のみをインストール
```

### コード品質
```bash
cd app
uv run ruff check   # コードをリント
uv run black .      # コードをフォーマット
```

### アプリケーション実行
```bash
cd app
uv run python main.py  # ローカル実行（ポート9100）
```

### Docker コマンド
```bash
# 本番イメージをビルド
docker-compose build prod

# 開発イメージをビルド
docker-compose build dev
```

## 主要エンドポイント

- `/` - ヘルスチェック
- `/health` - JSON形式のヘルス状態
- `/metrics` - Prometheus メトリクスエンドポイント（`?symbols=AAPL,GOOGL` パラメーター対応）
- `/api/stocks` - 株価データのデバッグAPI
- `/version` - アプリケーションバージョン情報

## アーキテクチャメモ

- API呼び出しを削減するため、株価データは5分間キャッシュされます
- メトリクスには現在価格、前日終値、価格変動、出来高、時価総額、PERが含まれます
- エラーメトリクスは取得失敗と処理エラーを追跡します
- URLパラメーターで複数の株式銘柄に対応します
- タイムゾーン対応のタイムスタンプを使用します（Asia/Tokyo）
