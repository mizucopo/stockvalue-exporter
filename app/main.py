"""メインアプリケーションモジュール."""

import logging

from flask import Flask
from prometheus_client import Counter, Histogram

from app import App
from base_view import BaseView
from config import config
from health_view import HealthView
from metrics_factory import MetricsFactory
from metrics_view import MetricsView
from stocks_view import StocksView
from version_view import VersionView

# ログ設定
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL))
logger = logging.getLogger(__name__)

web = Flask(__name__)

# MetricsFactoryインスタンスを作成（アプリケーション設定を渡す）
metrics_factory = MetricsFactory.create_default(app_config=config)


# アプリケーション起動時に情報を取得
app = App()
APP_NAME = app.name
APP_VERSION = app.version
APP_DESCRIPTION = app.description

# MetricsFactoryをappに設定（循環インポート解決）
app.set_metrics_factory(metrics_factory)

# StockDataFetcherのappへの初期化（統一メトリクス）
duration_metric = metrics_factory.get_metric("financial_fetch_duration")
errors_metric = metrics_factory.get_metric("financial_fetch_errors")

# 型安全性のチェック
if not isinstance(duration_metric, Histogram):
    raise TypeError(
        f"Expected Histogram for financial_fetch_duration, got {type(duration_metric)}"
    )
if not isinstance(errors_metric, Counter):
    raise TypeError(
        f"Expected Counter for financial_fetch_errors, got {type(errors_metric)}"
    )

app.initialize_fetcher(duration_metric, errors_metric)

# ビュークラスにアプリケーションインスタンスを設定（依存性注入）
BaseView.set_app_instance(app)

# URLルールの登録
web.add_url_rule("/", view_func=App.as_view("main"))
web.add_url_rule("/health", view_func=HealthView.as_view("health"))
web.add_url_rule("/version", view_func=VersionView.as_view("version"))
web.add_url_rule("/metrics", view_func=MetricsView.as_view("metrics"))
web.add_url_rule("/api/stocks", view_func=StocksView.as_view("stocks"))

if __name__ == "__main__":
    print(f"Starting {APP_NAME} v{APP_VERSION}")
    print(f"Description: {APP_DESCRIPTION}")
    print(f"Metrics available at: http://{config.HOST}:{config.PORT}/metrics")
    print(
        f"Example: http://{config.HOST}:{config.PORT}/metrics?symbols=AAPL,^GSPC,BTC-USD"
    )
    print(f"Environment: {'Production' if config.is_production else 'Development'}")
    web.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
