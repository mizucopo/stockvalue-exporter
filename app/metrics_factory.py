"""メトリクスファクトリーモジュール."""

from typing import Any

from prometheus_client import REGISTRY, CollectorRegistry, Counter, Gauge, Histogram


class MetricsFactory:
    """メトリクスを設定から動的に生成するファクトリークラス."""

    # デフォルトのメトリクス設定
    DEFAULT_METRICS_CONFIG = {
        "gauges": [
            {
                "name": "stock_price_current",
                "description": "Current stock price",
                "labels": ["symbol", "name", "currency", "exchange"],
                "key": "stock_price",
            },
            {
                "name": "stock_volume_current",
                "description": "Current stock volume",
                "labels": ["symbol", "name", "exchange"],
                "key": "stock_volume",
            },
            {
                "name": "stock_market_cap",
                "description": "Market capitalization",
                "labels": ["symbol", "name", "exchange"],
                "key": "stock_market_cap",
            },
            {
                "name": "stock_pe_ratio",
                "description": "Price to Earnings ratio",
                "labels": ["symbol", "name", "exchange"],
                "key": "stock_pe_ratio",
            },
            {
                "name": "stock_dividend_yield",
                "description": "Dividend yield percentage",
                "labels": ["symbol", "name", "exchange"],
                "key": "stock_dividend_yield",
            },
            {
                "name": "stock_52week_high",
                "description": "52 week high price",
                "labels": ["symbol", "name", "exchange"],
                "key": "stock_52week_high",
            },
            {
                "name": "stock_52week_low",
                "description": "52 week low price",
                "labels": ["symbol", "name", "exchange"],
                "key": "stock_52week_low",
            },
            {
                "name": "stock_previous_close",
                "description": "Previous day closing price",
                "labels": ["symbol", "name", "exchange"],
                "key": "stock_previous_close",
            },
            {
                "name": "stock_price_change",
                "description": "Price change from previous close",
                "labels": ["symbol", "name", "exchange"],
                "key": "stock_price_change",
            },
            {
                "name": "stock_price_change_percent",
                "description": "Price change percentage from previous close",
                "labels": ["symbol", "name", "exchange"],
                "key": "stock_price_change_percent",
            },
            {
                "name": "stock_last_updated_timestamp",
                "description": "Last updated timestamp",
                "labels": ["symbol"],
                "key": "stock_last_updated",
            },
            # 為替レート用メトリクス
            {
                "name": "forex_rate_current",
                "description": "Current forex exchange rate",
                "labels": ["symbol", "name", "currency", "exchange"],
                "key": "forex_rate",
            },
            {
                "name": "forex_previous_close",
                "description": "Previous day closing rate",
                "labels": ["symbol", "name", "exchange"],
                "key": "forex_previous_close",
            },
            {
                "name": "forex_rate_change",
                "description": "Rate change from previous close",
                "labels": ["symbol", "name", "exchange"],
                "key": "forex_rate_change",
            },
            {
                "name": "forex_rate_change_percent",
                "description": "Rate change percentage from previous close",
                "labels": ["symbol", "name", "exchange"],
                "key": "forex_rate_change_percent",
            },
            {
                "name": "forex_52week_high",
                "description": "52 week high rate",
                "labels": ["symbol", "name", "exchange"],
                "key": "forex_52week_high",
            },
            {
                "name": "forex_52week_low",
                "description": "52 week low rate",
                "labels": ["symbol", "name", "exchange"],
                "key": "forex_52week_low",
            },
            {
                "name": "forex_last_updated_timestamp",
                "description": "Last updated timestamp for forex",
                "labels": ["symbol"],
                "key": "forex_last_updated",
            },
            # 株価指数用メトリクス
            {
                "name": "index_value_current",
                "description": "Current index value",
                "labels": ["symbol", "name", "currency", "exchange"],
                "key": "index_value",
            },
            {
                "name": "index_volume_current",
                "description": "Current index volume",
                "labels": ["symbol", "name", "exchange"],
                "key": "index_volume",
            },
            {
                "name": "index_previous_close",
                "description": "Previous day closing value",
                "labels": ["symbol", "name", "exchange"],
                "key": "index_previous_close",
            },
            {
                "name": "index_value_change",
                "description": "Value change from previous close",
                "labels": ["symbol", "name", "exchange"],
                "key": "index_value_change",
            },
            {
                "name": "index_value_change_percent",
                "description": "Value change percentage from previous close",
                "labels": ["symbol", "name", "exchange"],
                "key": "index_value_change_percent",
            },
            {
                "name": "index_52week_high",
                "description": "52 week high value",
                "labels": ["symbol", "name", "exchange"],
                "key": "index_52week_high",
            },
            {
                "name": "index_52week_low",
                "description": "52 week low value",
                "labels": ["symbol", "name", "exchange"],
                "key": "index_52week_low",
            },
            {
                "name": "index_last_updated_timestamp",
                "description": "Last updated timestamp for index",
                "labels": ["symbol"],
                "key": "index_last_updated",
            },
            # 暗号通貨用メトリクス
            {
                "name": "crypto_price_current",
                "description": "Current cryptocurrency price",
                "labels": ["symbol", "name", "currency", "exchange"],
                "key": "crypto_price",
            },
            {
                "name": "crypto_volume_current",
                "description": "Current cryptocurrency volume",
                "labels": ["symbol", "name", "exchange"],
                "key": "crypto_volume",
            },
            {
                "name": "crypto_market_cap",
                "description": "Cryptocurrency market capitalization",
                "labels": ["symbol", "name", "exchange"],
                "key": "crypto_market_cap",
            },
            {
                "name": "crypto_previous_close",
                "description": "Previous day closing price",
                "labels": ["symbol", "name", "exchange"],
                "key": "crypto_previous_close",
            },
            {
                "name": "crypto_price_change",
                "description": "Price change from previous close",
                "labels": ["symbol", "name", "exchange"],
                "key": "crypto_price_change",
            },
            {
                "name": "crypto_price_change_percent",
                "description": "Price change percentage from previous close",
                "labels": ["symbol", "name", "exchange"],
                "key": "crypto_price_change_percent",
            },
            {
                "name": "crypto_52week_high",
                "description": "52 week high price",
                "labels": ["symbol", "name", "exchange"],
                "key": "crypto_52week_high",
            },
            {
                "name": "crypto_52week_low",
                "description": "52 week low price",
                "labels": ["symbol", "name", "exchange"],
                "key": "crypto_52week_low",
            },
            {
                "name": "crypto_last_updated_timestamp",
                "description": "Last updated timestamp for cryptocurrency",
                "labels": ["symbol"],
                "key": "crypto_last_updated",
            },
        ],
        "counters": [
            {
                "name": "stock_fetch_errors_total",
                "description": "Total stock fetch errors",
                "labels": ["symbol", "error_type"],
                "key": "stock_fetch_errors",
            },
            {
                "name": "forex_fetch_errors_total",
                "description": "Total forex fetch errors",
                "labels": ["symbol", "error_type"],
                "key": "forex_fetch_errors",
            },
            {
                "name": "index_fetch_errors_total",
                "description": "Total index fetch errors",
                "labels": ["symbol", "error_type"],
                "key": "index_fetch_errors",
            },
            {
                "name": "crypto_fetch_errors_total",
                "description": "Total cryptocurrency fetch errors",
                "labels": ["symbol", "error_type"],
                "key": "crypto_fetch_errors",
            },
        ],
        "histograms": [
            {
                "name": "stock_fetch_duration_seconds",
                "description": "Time spent fetching stock data",
                "labels": ["symbol"],
                "key": "stock_fetch_duration",
            },
            {
                "name": "forex_fetch_duration_seconds",
                "description": "Time spent fetching forex data",
                "labels": ["symbol"],
                "key": "forex_fetch_duration",
            },
            {
                "name": "index_fetch_duration_seconds",
                "description": "Time spent fetching index data",
                "labels": ["symbol"],
                "key": "index_fetch_duration",
            },
            {
                "name": "crypto_fetch_duration_seconds",
                "description": "Time spent fetching cryptocurrency data",
                "labels": ["symbol"],
                "key": "crypto_fetch_duration",
            },
        ],
    }

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        registry: CollectorRegistry | None = None,
        app_config: Any = None,
    ) -> None:
        """メトリクスファクトリーを初期化する.

        Args:
            config: メトリクス設定辞書。Noneの場合はデフォルト設定を使用
            registry: Prometheusレジストリ。Noneの場合はデフォルトレジストリを使用
            app_config: アプリケーション設定。メトリクス制御フラグを参照
        """
        self.config = config if config is not None else self.DEFAULT_METRICS_CONFIG
        self.registry = registry if registry is not None else REGISTRY
        self.app_config = app_config
        self.metrics = {}
        self._create_metrics()

    def _should_create_metric(self, metric_name: str) -> bool:
        """メトリクスを作成すべきかどうかを判定する.

        Args:
            metric_name: メトリクス名

        Returns:
            作成すべき場合True
        """
        if self.app_config is None:
            # 設定がない場合は全て作成
            return True

        # 52週系メトリクス（Range Metrics）の制御
        range_metric_patterns = ["52week_high", "52week_low"]
        if any(pattern in metric_name for pattern in range_metric_patterns):
            return getattr(self.app_config, "ENABLE_RANGE_METRICS", True)

        # デバッグ系メトリクス（Duration, Errors）の制御
        debug_metric_patterns = ["fetch_duration", "fetch_errors"]
        if any(pattern in metric_name for pattern in debug_metric_patterns):
            return getattr(self.app_config, "ENABLE_DEBUG_METRICS", True)

        # その他のメトリクスは常に作成
        return True

    def _create_metrics(self) -> None:
        """設定からメトリクスを生成する."""
        # Gaugeメトリクスを作成
        for gauge_config in self.config.get("gauges", []):
            if self._should_create_metric(gauge_config["name"]):
                metric = Gauge(
                    gauge_config["name"],
                    gauge_config["description"],
                    gauge_config["labels"],
                    registry=self.registry,
                )
                self.metrics[gauge_config["key"]] = metric

        # Counterメトリクスを作成
        for counter_config in self.config.get("counters", []):
            if self._should_create_metric(counter_config["name"]):
                metric = Counter(
                    counter_config["name"],
                    counter_config["description"],
                    counter_config["labels"],
                    registry=self.registry,
                )
                self.metrics[counter_config["key"]] = metric

        # Histogramメトリクスを作成
        for histogram_config in self.config.get("histograms", []):
            if self._should_create_metric(histogram_config["name"]):
                metric = Histogram(
                    histogram_config["name"],
                    histogram_config["description"],
                    histogram_config["labels"],
                    registry=self.registry,
                )
                self.metrics[histogram_config["key"]] = metric

    def get_metric(self, key: str) -> Gauge | Counter | Histogram | None:
        """キーでメトリクスを取得する.

        Args:
            key: メトリクスのキー

        Returns:
            指定されたキーのメトリクス、存在しない場合はNone
        """
        return self.metrics.get(key)

    def get_all_metrics(self) -> dict[str, Gauge | Counter | Histogram]:
        """すべてのメトリクスを取得する.

        Returns:
            すべてのメトリクスの辞書
        """
        return self.metrics

    def clear_all_metrics(self) -> None:
        """全てのメトリクスのデータをクリアする（レジストリからは削除しない）.

        注意: この操作により、全てのシンボルのメトリクスデータが削除されます。
        メトリクス自体はレジストリに残ります。
        """
        for metric in self.metrics.values():
            try:
                metric.clear()
            except Exception:
                # クリアに失敗した場合は無視
                pass

    def unregister_all_metrics(self) -> None:
        """全てのメトリクスをレジストリから完全に削除する.

        注意: この操作により、メトリクスがレジストリから完全に削除されます。
        再利用するには新しいMetricsFactoryインスタンスを作成する必要があります。
        """
        for metric in self.metrics.values():
            try:
                self.registry.unregister(metric)
            except KeyError:
                # メトリクスが既に削除されている場合は無視
                pass
            except Exception:
                # その他のエラーは無視
                pass

        # メトリクス辞書をクリア
        self.metrics.clear()

    def recreate_metrics(self) -> None:
        """全てのメトリクスを再作成する.

        既存のメトリクスをレジストリから削除してから、新しいメトリクスを作成します。
        """
        # 既存のメトリクスを削除
        self.unregister_all_metrics()

        # 新しいメトリクスを作成
        self._create_metrics()

    @classmethod
    def create_default(
        cls, registry: CollectorRegistry | None = None, app_config: Any = None
    ) -> "MetricsFactory":
        """デフォルト設定でMetricsFactoryインスタンスを作成する.

        Args:
            registry: Prometheusレジストリ。Noneの場合はデフォルトレジストリを使用
            app_config: アプリケーション設定。メトリクス制御フラグを参照

        Returns:
            デフォルト設定のMetricsFactoryインスタンス
        """
        return cls(registry=registry, app_config=app_config)
