# Gunicorn構成の比較と選定（Issue #73）

## 選定

既定を **1 worker / gthread / 4 threads / worker timeout 30秒** にする。
4 syncから常駐メモリと銘柄の重複取得を減らし、1 syncで発生した通信待ち中の
cached API・healthのブロックを避ける。cache missの取得とscrapeの出力を保護する
コード変更を同時に入れる。無修正のthreads構成は二重fetchと価格系列の混線が
再現したため採用しない。

4threadsは、通常のscrape、API、healthを同時に受け付ける小規模な用途を想定する。
Yahoo取得を並列化する設定ではない。cold missは直列化し、同時scrapeも消去から
出力まで直列化する。全threadsが処理・ロック待ちで埋まれば後続要求は待つ。
異なるcold銘柄を大量に並列取得する用途のcapacityは、この限定測定では判断しない。

## 環境と方法

2026-10-13に最新main `71df6b9ce4e2c370983b5e154a122b42266f5093` をbaselineとして測定。
PR #91の削除を含むbaseから分離し、依存・version・Yahoo取得手順は変更していない。
Python 3.14.8、Gunicorn 26.2.0、yfinance 1.7.0、prometheus-client 0.22.1。
Docker Desktop上のLinux arm64、各コンテナ2 CPU / 512 MiB、UID/GID 10001:10001。
比較時のimage IDは次のとおり。

- baseline: `sha256:a3f0926e1d95786b8e78b57c539e4c5c20ce918f07c67e1988c5e2b346fd401c`
- 修正候補: `sha256:d4dc14e17e4f19cd5577f30d14163ce0bd395c6738441ddad5cb65f4b9d0b047`

各imageの4 sync / 1 sync / 1 gthread・4threadsを各3回、別コンテナで逐次測定した。
実際の `src.main:web`・Ticker生成・fetcher・LRUCache・HTTP view・registryを使い、
`Ticker.info` だけ固定の辞書と遅延へ差し替える。通常の遅延は1銘柄100ms。
観測用のPID headerとcache lookup/fetch開始・終了の記録を追加している。
`--network none` とPython socket guardで外部取得を防ぐ。実Yahooリクエストは0件。

idleは全workerのimport完了後に測定。server RSSはmaster＋workerの合計であり、
共有pageを重複計上する。cgroup memoryにはコンテナ内の小さなHTTP測定プロセスも
含まれる。workload中は20ms間隔で採取し、cgroupのlifetime peakも終了時点で読む。
これらは意味が異なるため、RSS合計をコンテナの物理使用量として扱わない。

表は3回の中央値。warm応答は各回8要求の中央値を使い、全workerへ事前にcacheを
入れる。観測用ファイルI/Oも応答時間に含む。数msの差を性能順位とは解釈しない。

## メモリと応答時間

| 測定 | 現行4 sync | 無修正1 sync | 無修正1×4threads | 修正後1×4threads |
| --- | ---: | ---: | ---: | ---: |
| idle server RSS合計 (MiB) | 493.79 | 143.32 | 144.02 | 144.12 |
| idle cgroup memory (MiB) | 342.01 | 113.50 | 114.04 | 113.91 |
| workload中server RSS最大 (MiB) | 495.80 | 143.87 | 144.56 | 144.56 |
| workload中cgroup current最大 (MiB) | 344.54 | 115.00 | 115.14 | 115.33 |
| 終了時cgroup lifetime peak (MiB) | 344.54 | 119.29 | 119.58 | 119.76 |
| warm `/api/stocks` (ms) | 0.73 | 1.17 | 1.26 | 0.75 |
| warm `/metrics` (ms) | 1.28 | 1.24 | 1.56 | 1.30 |
| cold default 9銘柄scrape (ms) | 949.93 | 936.35 | 945.75 | 946.78 |
| cold最大12銘柄scrape (ms) | 1258.48 | 1247.66 | 1260.84 | 1256.66 |
| 1.2秒のcold API中、cached API (ms) | 1.45 | 1200.12 | 2.18 | 1.38 |
| 同じcold API中、`/health` (ms) | 1.01 | 1200.60 | 1.74 | 1.02 |

修正後1×4threadsのidle cgroupは現行比約66.7%減、RSS合計は約70.8%減。
idle cgroupの3回rangeは現行341.84–342.54 MiB、修正後113.77–114.10 MiB。
master RSSは約26.5 MiB、worker単体は約117 MiB。1 syncも同程度のメモリになるが、
通信待ち中にcached APIとhealthが待つため、通常のscrape＋API用途の既定には選ばない。

修正コードでも4 sync / 1 syncを各3回再測定した。idle cgroupは341.96 / 113.63 MiB、
warm APIは0.89 / 1.04ms、warm metricsは1.21 / 1.19ms、同時coldのfetchは4 / 1回。
1 syncのcached API待ちは1198.11msで、構成上の差は同じだった。

scrapeのHTTP送信直前からbody読取完了までの専用samplerでも補足測定した。
開始・終了snapshotと20ms周期、各scrape41–56 samples。次の表は各構成**1回**の
補足値で、上の3回中央値とは別の実験。値はserver RSS peak / cgroup current最大。

| 構成 | cold 9銘柄中 (MiB) | cold 12銘柄中 (MiB) |
| --- | ---: | ---: |
| 現行4 sync | 497.53 / 343.71 | 497.71 / 344.03 |
| 無修正1 sync | 144.20 / 114.64 | 144.28 / 114.80 |
| 無修正1×4threads | 144.39 / 114.84 | 144.47 / 115.21 |
| 修正後1×4threads | 144.55 / 114.54 | 144.61 / 114.92 |

## cache・fetchと同時要求

| シナリオ | 現行4 sync | 無修正1 sync | 無修正1×4threads | 修正後1×4threads |
| --- | --- | --- | --- | --- |
| 同一銘柄8連続要求のfetch回数（各run） | 2 / 2 / 1 | 1 / 1 / 1 | 1 / 1 / 1 | 1 / 1 / 1 |
| 上記lookup hit / miss | 6/2・6/2・7/1 | 各7/1 | 各7/1 | 各7/2 |
| 同一cold銘柄4同時要求のfetch回数 | 各4 | 各1 | 各4 | 各1 |
| 上記lookup hit / miss | 各0/4 | 各3/1 | 各0/4 | 各3/5 |
| warm API / metricsのfetch回数 | 0 | 0 | 0 | 0 |
| 異なる銘柄4同時scrape、全応答分離 | 3/3 runs | 3/3 runs | 0/3 runs | 3/3 runs |

4 syncの8連続要求はacceptの偏りで全workerに分散しない場合がある。
同時cold要求では異なる4 PIDが同じ銘柄を各1回取得した。cacheはworker間で共有されず、
1プロセス化後は1回の取得結果を全4要求が共有した。
修正後のlookup missには取得ロック内の再確認も含まれる。lookup回数とfetch回数を
混同しない。同時coldでは最初の4 miss＋取得者の再確認miss1、待機者のhit3になる。
全runのdefault9 / 最大12銘柄scrapeはfetch9 / 12回と要求銘柄集合を検査した。
benchmarkの価格数値の検査はAPI応答に対して行う。scrapeの価格数値は既存の
HTTP契約テストと追加の競合テストで検査し、9 / 12銘柄benchmarkでは検査していない。

安全策はLRU public操作のロックとsnapshot反復、プロセス共通のcold取得ロック・
取得前のcache再確認、scrape全体のロック。価格・JSON形式・TTL・LRUの上限は維持する。
debug系列は個々のPrometheus操作として保護されるが、同時API取得を含み得る。
従来どおりscrapeのclearでresetされ、要求全体の厳密なsnapshotや永続累計ではない。

## timeout

新しいコンテナで `--timeout 2` と5秒遅延の単一銘柄を各3回測定した。
4 syncは2.13–2.18秒、1 syncは2.45–2.93秒でHTTP 500となり、worker PIDが変わった。
各runで `WORKER TIMEOUT` を1件確認し、その後のhealthは200へ復旧した。
修正後gthreadは5.006–5.009秒で200、worker再生成・timeout logなしだった。

Gunicorn 26.2.0の `config.py` にあるtimeout定義と `workers/gthread.py` のheartbeatを
インストール済みソースでも確認した。既定30秒はworker無応答の監視として維持し、
HTTP要求の期限とは扱わない。syncの要求打切りとgthreadのheartbeat監視は異なる。
requestsの中断や銘柄全体のdeadlineは追加していない。yfinanceのHTTP timeoutは
個々の通信に適用され、複数通信・複数銘柄の合計時間はこれより長くなり得る。
既存の `REQUEST_TIMEOUT_SECONDS` / `MAX_RETRIES` はfetcherへ渡されていないため、
それらを変えることで要求を制限できるとは案内しない。

## 再現手順

```bash
mkdir -p /tmp/issue73-baseline-source
git archive 71df6b9ce4e2c370983b5e154a122b42266f5093 | tar -x -C /tmp/issue73-baseline-source
docker build -t stockvalue-exporter:issue-73-baseline /tmp/issue73-baseline-source
docker build -t stockvalue-exporter:issue-73-candidate .
uv run --frozen python benchmarks/gunicorn/run.py \
  --image stockvalue-exporter:issue-73-baseline \
  --output /tmp/issue-73-baseline.json --repeats 3
uv run --frozen python benchmarks/gunicorn/run.py \
  --image stockvalue-exporter:issue-73-candidate \
  --output /tmp/issue-73-candidate.json --repeats 3
```

測定は同時に走らせず、JSONの `runs` が9件で `harness_error` がないことを確認する。
JSONには各PIDのRSS、cache lookupとfetch、要求ごとの応答時間、応答分離結果、
worker再起動とtimeout log数を保存する。
現在のハーネスはcold 9 / 12銘柄の `result.scrape_memory` に専用samplerの結果も
保存する。補足実験は同じコマンドを別output先と `--repeats 1` で実行した。
詳細は [ハーネスの説明](../benchmarks/gunicorn/README.md) を参照。

## 回帰検証と実環境の区別

変更前120 tests（coverage 92.81%）、変更後130 tests（93.94%）、Ruff check / format、
mypy、80% coverage gateを検証。
競合テストは変更前に7件が失敗し、修正後は通過した。cache反復・eviction、coldの
二重取得、異なるfetcherの共有session利用、取得例外後のlock解放、cached取得、
自動・明示・強制clearでの価格系列分離、400 / 500時の出力、healthを検査した。
既存の全資産タイプのJSON・メトリクス契約と、PR #91の削除も維持している。

Dockerは実際のLinux imageで起動・測定するが、金融データはfixtureである。
実Yahooの応答時間・rate limit、native curlの一時メモリ、実運用scrapeの分布や
production負荷は測っていない。fixtureのfetch1回は `Ticker.info` 1回を意味し、
YahooへのHTTPリクエスト1回とは限らない。yfinanceの共有session利用は直列化するが、
その内部のthread safetyをfixtureだけで証明したとは扱わない。
公開前のproduction環境での負荷確認は、別の実環境確認として扱う。
