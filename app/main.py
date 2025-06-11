"""メインアプリケーションモジュール."""

import logging

from flask import Flask

from app import App
from health_view import HealthView
from metrics_factory import MetricsFactory
from metrics_view import MetricsView
from stocks_view import StocksView
from version_view import VersionView

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

web = Flask(__name__)

# MetricsFactoryインスタンスを作成（デフォルト設定を使用）
metrics_factory = MetricsFactory.create_default()


# アプリケーション起動時に情報を取得
app = App()
APP_NAME = app.name
APP_VERSION = app.version
APP_DESCRIPTION = app.description

# StockDataFetcherのappへの初期化
app.initialize_fetcher(
    metrics_factory.get_metric("stock_fetch_duration"),
    metrics_factory.get_metric("stock_fetch_errors"),
)

# URLルールの登録
web.add_url_rule("/", view_func=App.as_view("main"))
web.add_url_rule("/health", view_func=HealthView.as_view("health"))
web.add_url_rule("/version", view_func=VersionView.as_view("version"))
web.add_url_rule("/metrics", view_func=MetricsView.as_view("metrics"))
web.add_url_rule("/api/stocks", view_func=StocksView.as_view("stocks"))

if __name__ == "__main__":
    print(f"Starting {APP_NAME} v{APP_VERSION}")
    print(f"Description: {APP_DESCRIPTION}")
    print("Metrics available at: http://localhost:9100/metrics")
    print("Example: http://localhost:9100/metrics?symbols=AAPL,GOOGL,MSFT")
    web.run(host="0.0.0.0", port=9100, debug=False)
