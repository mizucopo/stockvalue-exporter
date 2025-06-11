import tomllib
import logging
from pathlib import Path
from flask import Flask, jsonify, request
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from datetime import datetime
from stock_fetcher import StockDataFetcher


# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


class Main:
    """メインアプリケーションクラス"""

    def __init__(self):
        self.app_info = self.get_app_info()
        self.name = self.app_info["name"]
        self.version = self.app_info["version"]
        self.description = self.app_info["description"]
        # StockDataFetcherインスタンスを初期化時に作成
        self.fetcher = StockDataFetcher(
            stock_fetch_duration=stock_fetch_duration,
            stock_fetch_errors=stock_fetch_errors,
        )

    def get_version(self):
        """pyproject.tomlからバージョンを取得"""
        try:
            # 現在のファイルと同じディレクトリのpyproject.tomlを読み込み
            pyproject_path = Path(__file__).parent / "pyproject.toml"

            if not pyproject_path.exists():
                return 1

            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
                return data.get("project", {}).get("version", "unknown")
        except Exception as e:
            print(f"Error reading version from pyproject.toml: {e}")
            return 1

    def get_app_info(self):
        """アプリケーション情報を取得"""
        try:
            pyproject_path = Path(__file__).parent / "pyproject.toml"

            if not pyproject_path.exists():
                return {
                    "name": "stockvalue-exporter",
                    "version": "unknown",
                    "description": "Unknown",
                }

            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
                project = data.get("project", {})
                return {
                    "name": project.get("name", "stockvalue-exporter"),
                    "version": project.get("version", "unknown"),
                    "description": project.get(
                        "description", "Stock value exporter for Prometheus"
                    ),
                }
        except Exception as e:
            print(f"Error reading app info from pyproject.toml: {e}")
            return {
                "name": "stockvalue-exporter",
                "version": "unknown",
                "description": "Unknown",
            }

    def update_prometheus_metrics(self, stock_data_dict):
        """PrometheusメトリクスをStock dataで更新"""
        for symbol, data in stock_data_dict.items():
            try:
                labels = {
                    "symbol": data["symbol"],
                    "name": data["name"],
                    "exchange": data["exchange"],
                }

                # 価格関連メトリクス
                stock_price.labels(
                    symbol=data["symbol"],
                    name=data["name"],
                    currency=data["currency"],
                    exchange=data["exchange"],
                ).set(data["current_price"])

                stock_volume.labels(**labels).set(data["volume"])
                stock_market_cap.labels(**labels).set(data["market_cap"])
                stock_pe_ratio.labels(**labels).set(data["pe_ratio"])
                stock_dividend_yield.labels(**labels).set(
                    data["dividend_yield"] * 100 if data["dividend_yield"] else 0
                )
                stock_52week_high.labels(**labels).set(data["fifty_two_week_high"])
                stock_52week_low.labels(**labels).set(data["fifty_two_week_low"])

                # 前日比関連メトリクス
                stock_previous_close.labels(**labels).set(data["previous_close"])
                stock_price_change.labels(**labels).set(data["price_change"])
                stock_price_change_percent.labels(**labels).set(
                    data["price_change_percent"]
                )

                # 最終更新時刻
                stock_last_updated.labels(symbol=data["symbol"]).set(data["timestamp"])

            except Exception as e:
                logger.error(f"Error updating metrics for {symbol}: {e}")
                stock_fetch_errors.labels(
                    symbol=symbol, error_type="metric_update_error"
                ).inc()

    def health(self):
        """ヘルスチェック"""
        return f"{self.name} v{self.version} is running!"

    def health_json(self):
        """ヘルスチェック（JSON形式）"""
        return jsonify(
            {
                "name": self.name,
                "version": self.version,
                "description": self.description,
                "status": "running",
                "message": f"{self.name} v{self.version} is running!",
            }
        )

    def version_info(self):
        """バージョン情報"""
        return jsonify(
            {
                "name": self.name,
                "version": self.version,
                "description": self.description,
            }
        )

    def metrics(self):
        """Prometheusメトリクスエンドポイント"""
        try:
            # URLパラメータから銘柄リストを取得（配列対応）
            symbols_list = request.args.getlist("symbols")

            if not symbols_list:
                # 単一パラメータの場合（カンマ区切り）
                symbols_param = request.args.get("symbols", "")
                if symbols_param:
                    symbols = [
                        s.strip().upper() for s in symbols_param.split(",") if s.strip()
                    ]
                else:
                    # デフォルト銘柄
                    symbols = ["AAPL", "GOOGL", "MSFT", "TSLA"]
            else:
                # 配列パラメータの場合
                symbols = [s.strip().upper() for s in symbols_list if s.strip()]

            if not symbols:
                logger.warning("No symbols provided for metrics collection")
                return (
                    generate_latest(),
                    200,
                    {"Content-Type": "text/plain; charset=utf-8"},
                )

            logger.info(f"Fetching metrics for symbols: {symbols}")

            # 株価データ取得
            stock_data = self.fetcher.get_stock_data(symbols)

            # メトリクス更新
            self.update_prometheus_metrics(stock_data)

            return generate_latest(), 200, {"Content-Type": "text/plain; charset=utf-8"}

        except Exception as e:
            logger.error(f"Error in metrics endpoint: {e}")
            return generate_latest(), 500, {"Content-Type": "text/plain; charset=utf-8"}

    def get_stocks(self):
        """株価データAPI（デバッグ用）"""
        # 配列パラメータ対応
        symbols_list = request.args.getlist("symbols")

        if not symbols_list:
            # 単一パラメータの場合（カンマ区切り）
            symbols_param = request.args.get("symbols", "AAPL,GOOGL")
            symbols = [s.strip().upper() for s in symbols_param.split(",") if s.strip()]
        else:
            # 配列パラメータの場合
            symbols = [s.strip().upper() for s in symbols_list if s.strip()]

        stock_data = self.fetcher.get_stock_data(symbols)

        return jsonify(
            {
                "timestamp": datetime.now().isoformat(),
                "symbols": symbols,
                "data": stock_data,
            }
        )


# アプリケーション起動時に情報を取得
main_app = Main()
APP_NAME = main_app.name
APP_VERSION = main_app.version
APP_DESCRIPTION = main_app.description

# Prometheusメトリクス定義
stock_price = Gauge(
    "stock_price_current",
    "Current stock price",
    ["symbol", "name", "currency", "exchange"],
)

stock_volume = Gauge(
    "stock_volume_current", "Current stock volume", ["symbol", "name", "exchange"]
)

stock_market_cap = Gauge(
    "stock_market_cap", "Market capitalization", ["symbol", "name", "exchange"]
)

stock_pe_ratio = Gauge(
    "stock_pe_ratio", "Price to Earnings ratio", ["symbol", "name", "exchange"]
)

stock_dividend_yield = Gauge(
    "stock_dividend_yield", "Dividend yield percentage", ["symbol", "name", "exchange"]
)

stock_52week_high = Gauge(
    "stock_52week_high", "52 week high price", ["symbol", "name", "exchange"]
)

stock_52week_low = Gauge(
    "stock_52week_low", "52 week low price", ["symbol", "name", "exchange"]
)

# 前日比関連メトリクス
stock_previous_close = Gauge(
    "stock_previous_close", "Previous day closing price", ["symbol", "name", "exchange"]
)

stock_price_change = Gauge(
    "stock_price_change",
    "Price change from previous close",
    ["symbol", "name", "exchange"],
)

stock_price_change_percent = Gauge(
    "stock_price_change_percent",
    "Price change percentage from previous close",
    ["symbol", "name", "exchange"],
)

# エラーメトリクス
stock_fetch_errors = Counter(
    "stock_fetch_errors_total", "Total stock fetch errors", ["symbol", "error_type"]
)

stock_fetch_duration = Histogram(
    "stock_fetch_duration_seconds", "Time spent fetching stock data", ["symbol"]
)

# 最終更新時刻
stock_last_updated = Gauge(
    "stock_last_updated_timestamp", "Last updated timestamp", ["symbol"]
)

# StockDataFetcherは stock_fetcher.py に移動しました
# update_prometheus_metricsはMainクラスに移動しました


# Flaskルートの設定
@app.route("/")
def health():
    return main_app.health()


@app.route("/health")
def health_json():
    return main_app.health_json()


@app.route("/version")
def version():
    return main_app.version_info()


@app.route("/metrics")
def metrics():
    return main_app.metrics()


@app.route("/api/stocks")
def get_stocks():
    return main_app.get_stocks()


if __name__ == "__main__":
    print(f"Starting {APP_NAME} v{APP_VERSION}")
    print(f"Description: {APP_DESCRIPTION}")
    print("Metrics available at: http://localhost:9100/metrics")
    print("Example: http://localhost:9100/metrics?symbols=AAPL,GOOGL,MSFT")
    app.run(host="0.0.0.0", port=9100, debug=False)
