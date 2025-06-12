# CLAUDE.md

このファイルは、このリポジトリでコードを扱う際の Claude Code (claude.ai/code) へのガイダンスを提供します。

## プロジェクト概要

Python と Flask を使用して構築された株価監視用の Prometheus カスタムエクスポーターです。
Yahoo Finance API から株価データを取得し、Prometheus メトリクスとして公開する高品質で拡張可能なアプリケーションです。

## アーキテクチャ概要

### 設計パターン

- **MVC パターン**: Model-View-Controller アーキテクチャ
- **Factory パターン**: MetricsFactory による設定駆動メトリクス生成
- **Template Method パターン**: BaseView による共通初期化パターン
- **Dependency Injection**: メトリクスのStockDataFetcherへの注入
- **Strategy パターン**: 設定可能なメトリクスタイプ

### クラス階層

```
MethodView (Flask)
├── App - アプリケーションメインクラス
└── BaseView - 全ビューの基底クラス
    ├── HealthView - ヘルスチェックエンドポイント
    ├── VersionView - バージョン情報エンドポイント
    ├── MetricsView - Prometheusメトリクスエンドポイント
    └── StocksView - 株価データJSONエンドポイント
```

## モジュール構成

### コアアプリケーション

- **`main.py`** - アプリケーションエントリーポイント
  - Flask アプリケーション設定
  - URL ルーティング設定
  - 依存性注入とメトリクス初期化

- **`app.py`** - メインアプリケーションクラス
  - Flask MethodView 継承
  - pyproject.toml からのメタデータ管理
  - StockDataFetcher 初期化

### ビューレイヤー

- **`base_view.py`** - 全ビューの抽象基底クラス
  - Flask MethodView 継承
  - アプリケーションインスタンスへの共通アクセス
  - 循環インポート対策

- **`health_view.py`** - ヘルスチェック (`/health`)
- **`version_view.py`** - バージョン情報 (`/version`)
- **`metrics_view.py`** - Prometheusメトリクス (`/metrics`)
  - 拡張された symbols パラメータ解析機能 (`_parse_symbols_parameter()`)
  - カンマ区切り、配列、混合形式のサポート
- **`stocks_view.py`** - 株価データAPI (`/api/stocks`)
  - 拡張された symbols パラメータ解析機能 (`_parse_symbols_parameter()`)
  - カンマ区切り、配列、混合形式のサポート

### ビジネスロジック

- **`stock_fetcher.py`** - 株価データ取得サービス
  - yfinance による Yahoo Finance API 連携
  - 10分間キャッシュ機能
  - Prometheus メトリクス統合
  - エラーハンドリングとフォールバック

- **`metrics_factory.py`** - メトリクス設定ファクトリー
  - 設定駆動でのメトリクス動的生成
  - Gauge、Counter、Histogram 対応
  - カスタムレジストリ管理

## API エンドポイント

| エンドポイント | メソッド | 説明 | パラメータ |
|-------------|---------|------|-----------|
| `/` | GET | アプリケーション状態 | なし |
| `/health` | GET | JSON形式ヘルスチェック | なし |
| `/version` | GET | アプリケーションバージョン情報 | なし |
| `/metrics` | GET | Prometheusメトリクス | `?symbols=AAPL,GOOGL` |
| `/api/stocks` | GET | 株価データJSON | `?symbols=AAPL,GOOGL` |

### パラメータ仕様

- **symbols**: 株式銘柄コード（複数形式をサポート）
  - **カンマ区切り**: `AAPL,GOOGL,MSFT,TSLA`
  - **配列形式**: `?symbols=AAPL&symbols=GOOGL&symbols=MSFT&symbols=TSLA`
  - **混合形式**: `?symbols=AAPL,GOOGL&symbols=MSFT&symbols=TSLA`
  - **重複除去**: 同じ銘柄が複数指定された場合、自動的に重複を除去し順序を保持
  - **デフォルト**: `AAPL,GOOGL,MSFT,TSLA`

## 開発環境設定

### 必要な環境

- **Docker**: Docker Engine & Docker Compose（必須）
- **Python**: 3.13+（Docker内で実行）
- **パッケージマネージャー**: uv（Docker内で実行）

> **注意**: 開発作業は全てDocker経由で行います。ローカルにPythonやuvのインストールは不要です。

### 開発ワークフロー

1. **本番イメージビルド**: `docker compose build prod`
2. **開発イメージビルド**: `docker compose build dev`
3. **コード開発**: エディタで編集
4. **品質チェック**: Docker経由でruff、black、mypy実行
5. **テスト実行**: Docker経由でpytest実行
6. **アプリケーション起動**: Docker経由で動作確認

### パッケージ管理（Docker経由）

```bash
# 開発依存関係を含む全依存関係をインストール
docker run --rm -v "$(pwd)":/workspace -w /workspace/app mizucopo/stockvalue-exporter:develop uv sync --dev

# 本番環境の依存関係のみをインストール
docker run --rm -v "$(pwd)":/workspace -w /workspace/app mizucopo/stockvalue-exporter:develop uv sync --no-dev
```

### コード品質ツール（Docker経由）

```bash
# リント実行
docker run --rm -v "$(pwd)":/workspace -w /workspace/app mizucopo/stockvalue-exporter:develop uv run ruff check .

# フォーマット実行
docker run --rm -v "$(pwd)":/workspace -w /workspace/app mizucopo/stockvalue-exporter:develop uv run black .

# 型チェック実行
docker run --rm -v "$(pwd)":/workspace -w /workspace/app mizucopo/stockvalue-exporter:develop uv run mypy .

# 全品質チェックを一括実行
docker run --rm -v "$(pwd)":/workspace -w /workspace/app mizucopo/stockvalue-exporter:develop sh -c "uv run ruff check . && uv run black . && uv run mypy ."
```

### テスト実行（Docker経由）

```bash
# 全テスト実行
docker run --rm -v "$(pwd)":/workspace -w /workspace mizucopo/stockvalue-exporter:develop uv run --dev python -m pytest tests/

# カバレッジ付き実行
docker run --rm -v "$(pwd)":/workspace -w /workspace mizucopo/stockvalue-exporter:develop uv run --dev python -m pytest tests/ --cov=. --cov-report=html

# 特定テスト実行
docker run --rm -v "$(pwd)":/workspace -w /workspace mizucopo/stockvalue-exporter:develop uv run --dev python -m pytest tests/test_app.py -v

# 短縮テスト実行（エラー時停止）
docker run --rm -v "$(pwd)":/workspace -w /workspace mizucopo/stockvalue-exporter:develop uv run --dev python -m pytest tests/ --tb=short -x
```

### アプリケーション実行（Docker経由）

```bash
# 開発サーバー起動（ポート9100）
docker run --rm -v "$(pwd)":/workspace -w /workspace/app -p 9100:9100 mizucopo/stockvalue-exporter:develop uv run python main.py

# または docker compose での起動
docker compose up dev
```

### Docker コマンド

```bash
# 本番イメージをビルド・実行
docker compose build prod
docker compose up prod

# 開発イメージをビルド・実行
docker compose build dev
docker compose up dev
```

## 依存関係

### 本番環境

- **Flask** (3.1.1+): ウェブフレームワーク
- **Gunicorn** (23.0.0+): WSGI サーバー
- **Pandas** (2.3.0+): データ処理
- **prometheus-flask-exporter** (0.23.2+): Prometheus統合
- **yfinance** (0.2.62+): Yahoo Finance API クライアント

### 開発環境

- **Black** (25.1.0+): コードフォーマッター
- **Ruff** (0.11.13+): リンター
- **MyPy** (1.15.0+): 型チェッカー
- **pytest** (8.3.0+): テストフレームワーク
- **pytest-cov** (6.0.0+): カバレッジ計測
- **pytest-mock** (3.14.0+): モックライブラリ

## テスト戦略

### テスト構成

- **カバレッジ**: 98% (目標: 80%以上)
- **テストファイル数**: 9ファイル
- **テスト数**: 59テスト（拡張されたパラメータサポートを含む）
- **フレームワーク**: pytest + フィクスチャーベース

### テストファイル

```
tests/
├── conftest.py              # テスト設定・フィクスチャー
├── test_app.py              # Appクラステスト
├── test_base_view.py        # BaseViewテスト
├── test_health_view.py      # HealthViewテスト
├── test_metrics_factory.py  # MetricsFactoryテスト
├── test_metrics_view.py     # MetricsViewテスト
├── test_stock_fetcher.py    # StockDataFetcherテスト
├── test_stocks_view.py      # StocksViewテスト
└── test_version_view.py     # VersionViewテスト
```

### テスト原則

- **ユニットテスト**: 包括的なモック化と分離
- **フィクスチャーベース**: pytest フィクスチャー活用
- **レジストリ管理**: テスト用独立Prometheusレジストリ
- **外部依存モック**: yfinance、ファイルシステム等のモック化

## メトリクス仕様

### Gauge メトリクス

- `stock_price_current`: 現在株価
- `stock_volume_current`: 現在出来高
- `stock_market_cap`: 時価総額
- `stock_pe_ratio`: PER
- `stock_dividend_yield`: 配当利回り（%）
- `stock_52week_high`: 52週最高値
- `stock_52week_low`: 52週最安値
- `stock_previous_close`: 前日終値
- `stock_price_change`: 価格変動
- `stock_price_change_percent`: 価格変動率（%）
- `stock_last_updated`: 最終更新時刻

### Counter メトリクス

- `stock_fetch_errors_total`: 株価取得エラー総数

### Histogram メトリクス

- `stock_fetch_duration_seconds`: 株価取得時間

### ラベル仕様

- **symbol**: 株式銘柄コード (例: AAPL)
- **name**: 会社名 (例: Apple Inc.)
- **currency**: 通貨 (例: USD)
- **exchange**: 取引所 (例: NASDAQ)
- **error_type**: エラータイプ (例: fetch_error, metric_update_error)

## 設定管理

### pyproject.toml 設定

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = ["-v", "--cov=.", "--cov-fail-under=80"]

[tool.black]
line-length = 88
target-version = ["py313"]

[tool.ruff]
target-version = "py313"
line-length = 88

[tool.mypy]
python_version = "3.13"
strict = true
```

## アーキテクチャメモ

### 特徴

- **高いテストカバレッジ**: 98%の包括的テストスイート
- **関心の分離**: 明確なレイヤー分離
- **拡張性**: ファクトリーパターンによる容易なメトリクス追加
- **監視機能**: 組み込みPrometheusメトリクス
- **エラー耐性**: 適切な劣化とエラーハンドリング
- **設定駆動**: 柔軟なメトリクス設定
- **モダンPython**: Python 3.13+ 機能と型ヒント活用

### キャッシュ戦略

- **TTL**: 10分間のメモリキャッシュ
- **対象**: 株価データ（APIコール削減）
- **実装**: 辞書ベースのシンプルキャッシュ

### エラーハンドリング

- **API エラー**: yfinance API失敗時の適切なフォールバック
- **メトリクスエラー**: エラーカウンターによる追跡
- **ログ記録**: 構造化ログでのデバッグ支援

### パフォーマンス

- **非同期なし**: シンプルな同期処理
- **キャッシュ最適化**: 不要なAPI呼び出し削減
- **メモリ効率**: 軽量なインメモリキャッシュ

### パラメータ解析機能

#### 実装詳細

**`_parse_symbols_parameter()` メソッド**
- **場所**: `MetricsView` および `StocksView` クラス
- **目的**: 複数形式のsymbols パラメータを統一的に処理
- **機能**:
  - URLパラメータから全ての symbols 値を取得
  - カンマ区切り文字列の分割処理
  - 配列形式パラメータの処理
  - 混合形式（カンマ区切り + 配列）の処理
  - 重複銘柄の自動除去（順序保持）
  - 空白文字の自動トリミング
  - 大文字変換による正規化

#### サポート形式

```python
# 以下の形式が全て同じ結果になる
?symbols=AAPL,GOOGL,MSFT          # カンマ区切り
?symbols=AAPL&symbols=GOOGL&symbols=MSFT    # 配列形式
?symbols=AAPL,GOOGL&symbols=MSFT            # 混合形式
?symbols=AAPL,GOOGL,AAPL&symbols=MSFT       # 重複あり（自動除去）
?symbols=  aapl  , googl  &symbols= msft    # 空白・小文字（自動正規化）
```

#### テストカバレッジ

新機能に対する包括的テストを追加：
- **混合パラメータテスト**: カンマ区切りと配列の組み合わせ
- **重複除去テスト**: 同一銘柄の重複指定処理
- **空白処理テスト**: 余分な空白文字の処理
- **デフォルト値テスト**: パラメータ未指定時の動作
- **エラーハンドリングテスト**: 不正なパラメータの処理

#### 利点

- **Prometheus互換性**: 配列形式パラメータを直接サポート
- **後方互換性**: 既存のカンマ区切り形式も引き続きサポート
- **柔軟性**: 用途に応じて最適な形式を選択可能
- **保守性**: 統一されたパラメータ解析ロジック

## トラブルシューティング

### よくある問題

1. **メトリクス重複エラー**: テスト時にはisolated_registryフィクスチャーを使用
2. **Yahoo Finance API制限**: キャッシュとエラーハンドリングで対応
3. **Flask コンテキストエラー**: テストではrequest_contextフィクスチャーを使用

### デバッグ方法

```bash
# アプリケーション起動（デバッグ用）
docker run --rm -v "$(pwd)":/workspace -w /workspace/app -p 9100:9100 -e LOG_LEVEL=DEBUG mizucopo/stockvalue-exporter:develop uv run python main.py

# 特定銘柄でのテスト（別ターミナル）
curl "http://localhost:9100/api/stocks?symbols=AAPL"

# メトリクス確認（複数形式をサポート）
curl "http://localhost:9100/metrics?symbols=AAPL,GOOGL"
curl "http://localhost:9100/metrics?symbols=AAPL&symbols=GOOGL"
curl "http://localhost:9100/metrics?symbols=AAPL,GOOGL&symbols=MSFT"

# コンテナ内でのデバッグ（インタラクティブシェル）
docker run --rm -it -v "$(pwd)":/workspace -w /workspace/app mizucopo/stockvalue-exporter:develop sh
```

### パフォーマンス監視

- Prometheusメトリクスでリクエスト時間を監視
- エラー率をstock_fetch_errors_totalで追跡
- 応答時間をstock_fetch_duration_secondsで測定

この仕様は継続的に更新され、アプリケーションの進化を反映します。
