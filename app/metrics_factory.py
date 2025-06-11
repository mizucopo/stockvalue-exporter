from prometheus_client import Counter, Gauge, Histogram


class MetricsFactory:
    """メトリクスを設定から動的に生成するファクトリークラス"""
    
    # デフォルトのメトリクス設定
    DEFAULT_METRICS_CONFIG = {
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
    
    def __init__(self, config=None):
        """
        メトリクスファクトリーを初期化
        
        Args:
            config: メトリクス設定辞書。Noneの場合はデフォルト設定を使用
        """
        self.config = config if config is not None else self.DEFAULT_METRICS_CONFIG
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
    
    @classmethod
    def create_default(cls):
        """デフォルト設定でMetricsFactoryインスタンスを作成"""
        return cls()