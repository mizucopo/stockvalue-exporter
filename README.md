# StockValue Exporter

高品質で拡張可能な**Prometheus カスタムエクスポーター**です。
Yahoo Finance API から**株価・指数・暗号通貨・為替データ**を取得し、リアルタイムでPrometheusメトリクスとして公開します。

[![Docker Hub](https://img.shields.io/docker/v/mizucopo/stockvalue-exporter?label=Docker%20Hub)](https://hub.docker.com/r/mizucopo/stockvalue-exporter)
[![Test Coverage](https://img.shields.io/badge/coverage-98%25-brightgreen)](https://github.com/mizu-copo/stockvalue-exporter)
[![Python](https://img.shields.io/badge/python-3.13+-blue)](https://www.python.org)

## ✨ 特徴

- 🎯 **高信頼性**: 98%テストカバレッジ、85+テスト（拡張されたパラメータサポートを含む）、包括的品質管理
- 🌐 **多資産対応**: **株式**・**指数**・**暗号通貨**・**為替**の包括的サポート
- 🏗️ **モダンアーキテクチャ**: MVC、Factory、DI パターンによる保守性の高い設計
- ⚡ **高性能**: 10分間キャッシュによるAPI制限対策
- 📊 **豊富なメトリクス**: 11種類のGaugeメトリクス、エラー追跡、パフォーマンス計測
- 🐳 **Docker Ready**: 開発・本番環境でのコンテナ化対応
- 🔧 **柔軟な設定**: 設定駆動でのメトリクス管理

## 🚀 クイックスタート

### Docker Compose（推奨）

```bash
# リポジトリクローン
git clone https://github.com/mizu-copo/stockvalue-exporter.git
cd stockvalue-exporter

# 本番環境で起動
docker compose up prod
```

### Docker単体実行

```bash
# 最新版を取得して起動
docker run -p 9100:9100 mizucopo/stockvalue-exporter:latest

# 特定バージョンで起動
docker run -p 9100:9100 mizucopo/stockvalue-exporter:2.1.0
```

アプリケーションが起動したら、ブラウザで http://localhost:9100 にアクセスして動作確認できます。

## 📡 API エンドポイント

| エンドポイント | 説明 | 例 |
|-------------|------|---|
| `/` | アプリケーション状態 | `curl http://localhost:9100/` |
| `/health` | ヘルスチェック（JSON） | `curl http://localhost:9100/health` |
| `/version` | バージョン情報 | `curl http://localhost:9100/version` |
| `/metrics` | Prometheusメトリクス | `curl http://localhost:9100/metrics` |
| `/api/stocks` | 株価データAPI | `curl http://localhost:9100/api/stocks` |

### パラメータ指定

複数銘柄・指数・暗号通貨を取得（複数の形式をサポート）：

```bash
# カンマ区切り（株式・指数・暗号通貨の混合）
curl "http://localhost:9100/metrics?symbols=AAPL,^GSPC,BTC-USD"

# 配列形式
curl "http://localhost:9100/metrics?symbols=AAPL&symbols=^N225&symbols=BTC-USD"

# 混合形式
curl "http://localhost:9100/metrics?symbols=AAPL,^GSPC&symbols=BTC-USD"

# 指数のみ
curl "http://localhost:9100/metrics?symbols=^GSPC,^NDX,^N225,998405.T"

# JSON API（すべての形式をサポート）
curl "http://localhost:9100/api/stocks?symbols=AAPL,BTC-USD"
curl "http://localhost:9100/api/stocks?symbols=^GSPC&symbols=^N225"
```

**重複除去**: 同じ銘柄が複数回指定された場合、自動的に重複を除去し最初の出現順序を保持します。

## 🔧 技術仕様

### アーキテクチャ

- **言語**: Python 3.13+
- **フレームワーク**: Flask with MethodView pattern
- **パッケージ管理**: uv (高速、モダン)
- **設計パターン**: MVC, Factory, Template Method, Dependency Injection
- **テスト**: pytest (98%カバレッジ、55テスト)
- **品質管理**: ruff, black, mypy

### 主要依存関係

- **Flask** (3.1.1+): ウェブフレームワーク
- **yfinance** (0.2.62+): Yahoo Finance API クライアント
- **prometheus-client**: メトリクス生成
- **pandas** (2.3.0+): データ処理

## 📊 Prometheusメトリクス

### 主要メトリクス

| メトリクス名 | タイプ | 説明 |
|------------|------|------|
| `stock_price_current` | Gauge | 現在株価 |
| `stock_volume_current` | Gauge | 出来高 |
| `stock_market_cap` | Gauge | 時価総額 |
| `stock_pe_ratio` | Gauge | PER |
| `stock_price_change_percent` | Gauge | 価格変動率（%） |
| `stock_fetch_errors_total` | Counter | 取得エラー総数 |
| `stock_fetch_duration_seconds` | Histogram | 取得時間 |

### ラベル

- `symbol`: 株式銘柄（例: AAPL）
- `name`: 会社名（例: Apple Inc.）
- `currency`: 通貨（例: USD）
- `exchange`: 取引所（例: NASDAQ）

### Prometheus設定例

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'stockvalue-exporter'
    static_configs:
      - targets: ['localhost:9100']
    scrape_interval: 30s
    params:
      # カンマ区切り形式
      symbols: ['AAPL,GOOGL,MSFT,TSLA']

      # または配列形式
      # symbols: ['AAPL', 'GOOGL', 'MSFT', 'TSLA']
```

## 🛠️ 開発環境

### 前提条件

- Docker & Docker Compose（必須）
- ローカルにPython/uvのインストールは不要

### 開発ワークフロー

```bash
# 1. 本番イメージビルド
docker compose build prod

# 2. 開発イメージビルド
docker compose build dev

# 3. 依存関係インストール
docker run --rm -v "$(pwd)":/workspace -w /workspace/app mizucopo/stockvalue-exporter:develop uv sync --dev

# 4. コード品質チェック
docker run --rm -v "$(pwd)":/workspace -w /workspace/app mizucopo/stockvalue-exporter:develop uv run ruff check .

# 5. テスト実行
docker run --rm -v "$(pwd)":/workspace -w /workspace mizucopo/stockvalue-exporter:develop uv run --dev python -m pytest tests/

# 6. 開発サーバー起動
docker compose up dev
```

### コード品質

本プロジェクトは、4つの厳格な品質ツールで高品質なコードベースを維持しています：

#### 品質メトリクス

- **テストカバレッジ**: 82% ✅ (目標: 80%以上達成)
- **テスト数**: 113テスト（包括的なユニットテスト、11ファイル）
- **Ruff エラー**: 87 📈 (改善: 187→87、100個削減)
- **MyPy**: strict モード準拠 ✅ (型安全性確保)
- **Black**: 統一フォーマット ✅ (27ファイル、変更なし)

#### 4つのコード品質ツール

**1. Ruff - 高速Pythonリンター**
- Flake8、isort、pydocstyle等を統合
- コードスタイル、セキュリティ問題を検出
- 自動修正機能付き

**2. Black - コードフォーマッター**
- PEP8準拠の自動フォーマット
- 88文字行長制限
- 一貫したコードスタイル強制

**3. MyPy - 静的型チェッカー**
- 型ヒント基づく検証
- strict モード運用
- 実行時エラーの事前検出

**4. Pytest - テストフレームワーク**
- カバレッジ測定機能
- フィクスチャベーステスト
- 包括的なテストスイート

#### 品質チェック実行

```bash
# 統合品質チェック
docker run --rm -v "$(pwd)":/workspace -w /workspace/app mizucopo/stockvalue-exporter:develop sh -c "uv run black . && uv run ruff check . --fix && uv run mypy . && cd .. && uv run --dev python -m pytest tests/ --cov=. --cov-fail-under=80"

# 個別実行
docker run --rm -v "$(pwd)":/workspace -w /workspace/app mizucopo/stockvalue-exporter:develop uv run ruff check .        # リント
docker run --rm -v "$(pwd)":/workspace -w /workspace/app mizucopo/stockvalue-exporter:develop uv run black .          # フォーマット
docker run --rm -v "$(pwd)":/workspace -w /workspace/app mizucopo/stockvalue-exporter:develop uv run mypy .           # 型チェック
docker run --rm -v "$(pwd)":/workspace -w /workspace mizucopo/stockvalue-exporter:develop uv run --dev python -m pytest tests/ --cov=.  # テスト
```

## ⚙️ 設定

### 環境変数

| 変数名 | デフォルト | 説明 |
|-------|----------|------|
| `LOG_LEVEL` | `INFO` | ログレベル（DEBUG, INFO, WARNING, ERROR） |
| `PORT` | `9100` | サーバーポート |

### デフォルト銘柄

設定なしの場合、以下の銘柄が監視対象となります：
- AAPL (Apple Inc.)
- GOOGL (Alphabet Inc.)
- MSFT (Microsoft Corporation)
- TSLA (Tesla, Inc.)

## 🔄 キャッシュ戦略

- **TTL**: 10分間のメモリキャッシュ
- **対象**: 株価データ（Yahoo Finance API制限対策）
- **実装**: 辞書ベースのシンプルキャッシュ

API制限を回避しつつ、適度に新鮮なデータを提供します。

## 📈 利用例

### Grafana ダッシュボード

Prometheusと組み合わせてGrafanaでビジュアライゼーション：

```promql
# 株価チャート
stock_price_current{symbol="AAPL"}

# 価格変動率
stock_price_change_percent{symbol=~"AAPL|GOOGL|MSFT|TSLA"}

# エラー率監視
rate(stock_fetch_errors_total[5m])
```

### アラート設定

```yaml
# alert.yml
groups:
  - name: stock-monitoring
    rules:
      - alert: StockFetchErrors
        expr: rate(stock_fetch_errors_total[5m]) > 0.1
        for: 2m
        annotations:
          summary: "株価データ取得エラーが多発しています"
```

## 🤝 貢献

プロジェクトへの貢献を歓迎します！

### 貢献手順

1. Fork して feature ブランチを作成
2. Docker環境でコード開発
3. テスト実行・品質チェック
4. Pull Request 送信

### 開発ガイドライン

- 新機能は必ずテストを追加（カバレッジ80%以上維持）
- コミット前に `ruff`、`black`、`mypy` 実行
- コミットメッセージは英語で簡潔に

## 📝 ライセンス

このプロジェクトは [MIT License](LICENSE) の下で公開されています。

## 📞 サポート

- **Issues**: [GitHub Issues](https://github.com/mizu-copo/stockvalue-exporter/issues)
- **X (Twitter)**: [@mizu_copo](https://twitter.com/mizu_copo)
- **Docker Hub**: [mizucopo/stockvalue-exporter](https://hub.docker.com/r/mizucopo/stockvalue-exporter)

---

<div align="center">

**StockValue Exporter** - Built with ❤️ by [mizu](https://github.com/mizu-copo)

</div>
