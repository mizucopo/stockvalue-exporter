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

# Prometheusメトリクス設定
METRICS_CONFIG = {
    'gauges': [
        {
            'name': 'stock_price_current',
            'description': 'Current stock price',
            'labels': ['symbol', 'name', 'currency', 'exchange'],
            'key': 'stock_price'
        },
        {
            'name': 'stock_volume_current',
            'description': 'Current stock volume',
            'labels': ['symbol', 'name', 'exchange'],
            'key': 'stock_volume'
        },
        {
            'name': 'stock_market_cap',
            'description': 'Market capitalization',
            'labels': ['symbol', 'name', 'exchange'],
            'key': 'stock_market_cap'
        },
        {
            'name': 'stock_pe_ratio',
            'description': 'Price to Earnings ratio',
            'labels': ['symbol', 'name', 'exchange'],
            'key': 'stock_pe_ratio'
        },
        {
            'name': 'stock_dividend_yield',
            'description': 'Dividend yield percentage',
            'labels': ['symbol', 'name', 'exchange'],
            'key': 'stock_dividend_yield'
        },
        {
            'name': 'stock_52week_high',
            'description': '52 week high price',
            'labels': ['symbol', 'name', 'exchange'],
            'key': 'stock_52week_high'
        },
        {
            'name': 'stock_52week_low',
            'description': '52 week low price',
            'labels': ['symbol', 'name', 'exchange'],
            'key': 'stock_52week_low'
        },
        {
            'name': 'stock_previous_close',
            'description': 'Previous day closing price',
            'labels': ['symbol', 'name', 'exchange'],
            'key': 'stock_previous_close'
        },
        {
            'name': 'stock_price_change',
            'description': 'Price change from previous close',
            'labels': ['symbol', 'name', 'exchange'],
            'key': 'stock_price_change'
        },
        {
            'name': 'stock_price_change_percent',
            'description': 'Price change percentage from previous close',
            'labels': ['symbol', 'name', 'exchange'],
            'key': 'stock_price_change_percent'
        },
        {
            'name': 'stock_last_updated_timestamp',
            'description': 'Last updated timestamp',
            'labels': ['symbol'],
            'key': 'stock_last_updated'
        }
    ],
    'counters': [
        {
            'name': 'stock_fetch_errors_total',
            'description': 'Total stock fetch errors',
            'labels': ['symbol', 'error_type'],
            'key': 'stock_fetch_errors'
        }
    ],
    'histograms': [
        {
            'name': 'stock_fetch_duration_seconds',
            'description': 'Time spent fetching stock data',
            'labels': ['symbol'],
            'key': 'stock_fetch_duration'
        }
    ]
}


class MetricsFactory:
    """メトリクスを設定から動的に生成するファクトリークラス"""
    
    def __init__(self, config):
        self.config = config
        self.metrics = {}
        self._create_metrics()
    
    def _create_metrics(self):
        """設定からメトリクスを生成"""
        # Gaugeメトリクスを作成
        for gauge_config in self.config.get('gauges', []):
            metric = Gauge(
                gauge_config['name'],
                gauge_config['description'],
                gauge_config['labels']
            )
            self.metrics[gauge_config['key']] = metric
        
        # Counterメトリクスを作成
        for counter_config in self.config.get('counters', []):
            metric = Counter(
                counter_config['name'],
                counter_config['description'],
                counter_config['labels']
            )
            self.metrics[counter_config['key']] = metric
        
        # Histogramメトリクスを作成
        for histogram_config in self.config.get('histograms', []):
            metric = Histogram(
                histogram_config['name'],
                histogram_config['description'],
                histogram_config['labels']
            )
            self.metrics[histogram_config['key']] = metric
    
    def get_metric(self, key):
        """キーでメトリクスを取得"""
        return self.metrics.get(key)
    
    def get_all_metrics(self):
        """すべてのメトリクスを取得"""
        return self.metrics


# MetricsFactoryインスタンスを作成
metrics_factory = MetricsFactory(METRICS_CONFIG)

# 後方互換性のため、従来の変数名でもアクセス可能にする
stock_price = metrics_factory.get_metric('stock_price')
stock_volume = metrics_factory.get_metric('stock_volume')
stock_market_cap = metrics_factory.get_metric('stock_market_cap')
stock_pe_ratio = metrics_factory.get_metric('stock_pe_ratio')
stock_dividend_yield = metrics_factory.get_metric('stock_dividend_yield')
stock_52week_high = metrics_factory.get_metric('stock_52week_high')
stock_52week_low = metrics_factory.get_metric('stock_52week_low')
stock_previous_close = metrics_factory.get_metric('stock_previous_close')
stock_price_change = metrics_factory.get_metric('stock_price_change')
stock_price_change_percent = metrics_factory.get_metric('stock_price_change_percent')
stock_last_updated = metrics_factory.get_metric('stock_last_updated')
stock_fetch_errors = metrics_factory.get_metric('stock_fetch_errors')
stock_fetch_duration = metrics_factory.get_metric('stock_fetch_duration')

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
