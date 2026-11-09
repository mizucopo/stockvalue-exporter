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

コンテナは専用の `appuser`（UID/GID `10001:10001`）で実行されます。
アプリケーションの配置先 `/app` は実行時に書き込み不可で、必要なキャッシュは
`/home/appuser/.cache` に保存されます。

### Gunicorn とキャッシュ

Docker の既定は **1 worker、`gthread`、4 threads、worker timeout 30秒** です。
1プロセス内で `/metrics` と `/api/stocks` のキャッシュを共有し、複数workerで
同じ銘柄を再取得することと、Python・yfinanceの常駐メモリ重複を抑えます。
キャッシュのTTLと最大件数は従来どおりです。workerの再起動でキャッシュは失われ、
複数コンテナ間では共有されません。

cache miss時のyfinance取得はプロセス内で直列化し、待機後にキャッシュを再確認
します。同じ銘柄の同時取得は成功した結果を共有します。取得失敗はキャッシュに
保存せず、次の要求で再試行します。取得中でもcached APIや `/health` は別threadで
処理できます。異なる未取得銘柄の要求は待機し、全4threadsが処理・待機中なら
healthもqueueで待ちます。複数workerへの変更は、この待ち時間とメモリ・重複取得の
トレードオフを実際の負荷で確認してから行ってください。

`LRUCache` は操作をロックで保護し、キーの反復はsnapshotを返します。
同時scrapeはメトリクスの消去から出力まで直列化し、既定の自動消去が有効な場合は
価格系列を要求銘柄ごとに分離します。debugの取得時間・エラー系列はプロセス共有で、
同時API取得を含む場合があります。従来どおりmetricsの消去時にresetされるため、
プロセス起動以来の累計や要求単位の厳密なsnapshotではありません。

`--timeout 30` はworkerのheartbeatが途絶えた場合の再起動設定です。`gthread` では
通信待ちでもheartbeatを送るため、30秒でHTTP要求を打ち切る設定にはなりません。
yfinanceの個々の通信timeoutと、複数通信・銘柄取得を含む要求全体の所要時間は別です。
Prometheusの `scrape_timeout` は実際のcold scrape時間に合わせ、必要なら銘柄数を
減らしてください。クライアントのtimeout後もサーバー側の取得処理は続くことが
あります。Yahooの取得手順・timeout・retryの設定はこの変更では変えていません。

1 sync workerで実行する場合は、Dockerのコマンドを置き換えます。

```bash
docker run --rm -p 9100:9100 mizucopo/stockvalue-exporter:latest \
  gunicorn --workers 1 --worker-class sync --threads 1 --timeout 30 \
  --bind 0.0.0.0:9100 --chdir /app src.main:web
```

構成の比較結果と再現手順は [Gunicorn測定](docs/gunicorn-benchmark.md) を参照してください。

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
| `financial_fetch_errors_total` | メトリクス消去後のデータ取得エラー数 |
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

未使用だった `REQUEST_TIMEOUT_SECONDS` と `MAX_RETRIES` は削除しました。
旧環境変数が残っていても無視されるため、設定から削除できます。
外部のPythonコードで同名の `Config` 属性を直接参照している場合は、その参照も削除してください。
取得のtimeout・retryを制御する代替設定はなく、yfinanceによる取得動作は従来どおりです。

環境変数は `docker run` の `-e` オプションで指定できます。

```bash
docker run --rm -p 9100:9100 \
  -e DEFAULT_SYMBOLS="AAPL,MSFT,^N225" \
  -e CACHE_TTL_SECONDS=300 \
  mizucopo/stockvalue-exporter:latest
```

## 開発

### 必要なもの

- Python 3.14 以降
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
uv run task check
```

本番用および開発用の Docker イメージは、リポジトリのルートでビルドできます。

```bash
docker compose build prod
docker compose build dev
```

## リリース

Pull Request は squash merge します。`main` への push で `.github/workflows/docker-release.yml` が起動し、最新のマージ済み PR の `release:patch`・`release:minor`・`release:major` ラベルに応じて自動採番します。分類ラベルがない PR では公開をスキップします。

リリースでは、`pyproject.toml` を更新した採番コミットと同じソースから次を実行します。

- `linux/amd64` と `linux/arm64` のDockerイメージをDocker Hubへ公開
- `latest` とバージョン番号のDocker image tagを作成
- `v<version>` 形式のGit tagを作成
- GitHub Releaseを作成

Docker HubへのログインにはGitHub Actions secret `DOCKERHUB_TOKEN` を使用します。移行前の `DOCKER_TOKEN` も互換入力として利用できます。

分類基準は [CONTRIBUTING.md](CONTRIBUTING.md#リリース分類)、設定と復旧手順は [docs/release.md](docs/release.md) を参照してください。

## ライセンス

このプロジェクトは [MIT License](LICENSE) の下で公開されています。
