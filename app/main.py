import logging
from flask import Flask
from prometheus_client import Counter, Gauge, Histogram
from main_class import Main
from health_view import HealthView
from version_view import VersionView
from metrics_view import MetricsView
from stocks_view import StocksView

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

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

# アプリケーション起動時に情報を取得
main_app = Main()
APP_NAME = main_app.name
APP_VERSION = main_app.version
APP_DESCRIPTION = main_app.description

# StockDataFetcherのmain_appへの初期化
main_app.initialize_fetcher(stock_fetch_duration, stock_fetch_errors)

# URLルールの登録
app.add_url_rule("/", view_func=Main.as_view("main"))
app.add_url_rule("/health", view_func=HealthView.as_view("health"))
app.add_url_rule("/version", view_func=VersionView.as_view("version"))
app.add_url_rule("/metrics", view_func=MetricsView.as_view("metrics"))
app.add_url_rule("/api/stocks", view_func=StocksView.as_view("stocks"))

if __name__ == "__main__":
    print(f"Starting {APP_NAME} v{APP_VERSION}")
    print(f"Description: {APP_DESCRIPTION}")
    print("Metrics available at: http://localhost:9100/metrics")
    print("Example: http://localhost:9100/metrics?symbols=AAPL,GOOGL,MSFT")
    app.run(host="0.0.0.0", port=9100, debug=False)
