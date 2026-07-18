# StockValue Exporter

StockValue Exporter は、Yahoo Finance から株式、指数、暗号資産、為替のデータを取得し、Prometheus 形式のメトリクスとして公開するエクスポーターです。金融データを確認するための JSON API も提供します。

## 主な機能

- 株式、指数、暗号資産、為替に対応
- Prometheus 形式のメトリクスを公開
- シンボルを指定できる JSON API
- API へのアクセスを抑えるインメモリキャッシュ
- Docker イメージによる実行

## クイックスタート

Docker イメージを起動します。

```bash
docker run --rm -p 9100:9100 mizucopo/stockvalue-exporter:latest
```

起動後、メトリクスを取得できます。

```bash
curl "http://localhost:9100/metrics?symbols=AAPL,^N225,BTC-USD"
```

JSON でデータを確認する場合は、`/api/stocks` を使用します。

```bash
curl "http://localhost:9100/api/stocks?symbols=AAPL,^N225,BTC-USD"
```

## API

| エンドポイント | 説明 |
| --- | --- |
| `GET /` | アプリケーションの稼働状態を返します。 |
| `GET /health` | ヘルスチェック結果を JSON で返します。 |
| `GET /version` | アプリケーションのバージョン情報を返します。 |
| `GET /metrics` | Prometheus 形式のメトリクスを返します。 |
| `GET /api/stocks` | 金融データを JSON で返します。 |

`/metrics` と `/api/stocks` は、`symbols` クエリパラメータを受け付けます。カンマ区切り、同名パラメータの繰り返し、またはその組み合わせで指定できます。

```bash
curl "http://localhost:9100/metrics?symbols=AAPL,MSFT"
curl "http://localhost:9100/metrics?symbols=AAPL&symbols=MSFT"
```

`symbols` を省略した場合は、設定されたデフォルトシンボルを使用します。重複したシンボルは、最初に現れた順序を保って除去されます。

## Prometheus の設定例

```yaml
scrape_configs:
  - job_name: stockvalue-exporter
    static_configs:
      - targets:
          - localhost:9100
    params:
      symbols:
        - AAPL,^N225,BTC-USD
```

公開される主なメトリクスは次のとおりです。

| メトリクス | 説明 |
| --- | --- |
| `financial_price_current` | 現在価格、レート、または値 |
| `financial_volume_current` | 出来高 |
| `financial_previous_close` | 前日終値 |
| `financial_price_change` | 前日終値からの変動額 |
| `financial_price_change_percent` | 前日終値からの変動率 |
| `financial_market_cap` | 時価総額 |
| `financial_last_updated_timestamp` | データの最終更新時刻 |
| `financial_fetch_errors_total` | データ取得エラーの累計 |
| `financial_fetch_duration_seconds` | データ取得時間 |

メトリクスには、対象に応じて `symbol`、`name`、`currency`、`exchange`、`asset_type` などのラベルが付与されます。

## 設定

主な環境変数は次のとおりです。

| 環境変数 | デフォルト | 説明 |
| --- | --- | --- |
| `DEFAULT_SYMBOLS` | `AAPL,GOOGL,MSFT,TSLA,^GSPC,^NDX,998405.T,^N225,BTC-USD` | `symbols` を省略した場合の対象 |
| `MAX_SYMBOLS_PER_REQUEST` | `12` | 1リクエストで指定できるシンボル数 |
| `CACHE_TTL_SECONDS` | `600` | キャッシュの有効期間（秒） |
| `CACHE_MAX_SIZE` | `100` | キャッシュの最大エントリ数 |
| `AUTO_CLEAR_METRICS` | `true` | リクエストごとに既存のメトリクスをクリアするかどうか |
| `LOG_LEVEL` | `INFO` | ログレベル |
| `ENVIRONMENT` | `development` | 実行環境。`production` ではデバッグ用メトリクスが既定で無効になります。 |
| `ENABLE_DEBUG_METRICS` | 実行環境による | 取得時間と取得エラーのメトリクスを有効にするかどうか |

環境変数は `docker run` の `-e` オプションで指定できます。

```bash
docker run --rm -p 9100:9100 \
  -e DEFAULT_SYMBOLS="AAPL,MSFT,^N225" \
  -e CACHE_TTL_SECONDS=300 \
  mizucopo/stockvalue-exporter:latest
```

## 開発

### 必要なもの

- Python 3.13.5 以降
- [uv](https://docs.astral.sh/uv/)
- Docker および Docker Compose（イメージをビルドする場合）

依存関係をインストールします。

```bash
uv sync --locked
```

開発サーバーを起動します。

```bash
uv run python -m src.main
```

テストと静的解析を実行します。

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy .
```

本番用および開発用の Docker イメージは、リポジトリのルートでビルドできます。

```bash
docker compose build prod
docker compose build dev
```

## リリース

`main` への push で `.github/workflows/docker-release.yml` が起動します。通常は Pull Request を `main` へ merge してリリースします。

リリースでは、`pyproject.toml` のバージョンを使用して次を実行します。

- `linux/amd64` と `linux/arm64` のDockerイメージをDocker Hubへ公開
- `latest` とバージョン番号のDocker image tagを作成
- `v<version>` 形式のGit tagを作成
- GitHub Releaseを作成

Docker Hubへのログインには、GitHub Actions secret `DOCKER_TOKEN` を使用します。

## ライセンス

このプロジェクトは [MIT License](LICENSE) の下で公開されています。
