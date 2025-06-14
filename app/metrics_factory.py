"""メトリクスファクトリーモジュール."""

from typing import Any, Protocol

from prometheus_client import REGISTRY, CollectorRegistry, Counter, Gauge, Histogram


class ConfigProtocol(Protocol):
    """設定オブジェクトのプロトコル."""

    ENABLE_DEBUG_METRICS: bool


class MetricsFactory:
    """メトリクスを設定から動的に生成するファクトリークラス."""

    # 統一メトリクス設定（全資産タイプを1つのメトリクスで処理）
    DEFAULT_METRICS_CONFIG = {
        "gauges": [
            # 共通価格・値・レートメトリクス
            {
                "name": "financial_price_current",
                "description": "Current financial instrument price/rate/value",
                "labels": ["symbol", "name", "currency", "exchange", "asset_type"],
                "key": "financial_price",
            },
            {
                "name": "financial_volume_current",
                "description": "Current financial instrument volume",
                "labels": ["symbol", "name", "exchange", "asset_type"],
                "key": "financial_volume",
            },
            {
                "name": "financial_previous_close",
                "description": "Previous day closing price/rate/value",
                "labels": ["symbol", "name", "exchange", "asset_type"],
                "key": "financial_previous_close",
            },
            {
                "name": "financial_price_change",
                "description": "Price/rate/value change from previous close",
                "labels": ["symbol", "name", "exchange", "asset_type"],
                "key": "financial_price_change",
            },
            {
                "name": "financial_price_change_percent",
                "description": "Price/rate/value change percentage from previous close",
                "labels": ["symbol", "name", "exchange", "asset_type"],
                "key": "financial_price_change_percent",
            },
            {
                "name": "financial_last_updated_timestamp",
                "description": "Last updated timestamp for financial data",
                "labels": ["symbol", "asset_type"],
                "key": "financial_last_updated",
            },
            # 資産タイプ特有メトリクス
            {
                "name": "financial_market_cap",
                "description": "Market capitalization (stock/crypto only)",
                "labels": ["symbol", "name", "exchange", "asset_type"],
                "key": "financial_market_cap",
            },
        ],
        "counters": [
            {
                "name": "financial_fetch_errors_total",
                "description": "Total financial data fetch errors",
                "labels": ["symbol", "error_type", "asset_type"],
                "key": "financial_fetch_errors",
            },
        ],
        "histograms": [
            {
                "name": "financial_fetch_duration_seconds",
                "description": "Time spent fetching financial data",
                "labels": ["symbol", "asset_type"],
                "key": "financial_fetch_duration",
            },
        ],
    }

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        registry: CollectorRegistry | None = None,
        app_config: ConfigProtocol | None = None,
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
        self.metrics: dict[str, Gauge | Counter | Histogram] = {}
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

        # デバッグ系メトリクス（Duration, Errors）の制御
        # 統一メトリクスでは financial_fetch_duration と financial_fetch_errors が対象
        debug_metric_patterns = ["fetch_duration", "fetch_errors"]
        if any(pattern in metric_name for pattern in debug_metric_patterns):
            return getattr(self.app_config, "ENABLE_DEBUG_METRICS", True)

        # その他のメトリクスは常に作成
        # 注意: 統一メトリクス実装により、レンジメトリクスは廃止されました
        return True

    def _create_metrics(self) -> None:
        """設定からメトリクスを生成する."""
        # Gaugeメトリクスを作成
        for gauge_config in self.config.get("gauges", []):
            name = str(gauge_config["name"])
            if self._should_create_metric(name):
                metric = Gauge(
                    name,
                    str(gauge_config["description"]),
                    list(gauge_config["labels"]),
                    registry=self.registry,
                )
                self.metrics[str(gauge_config["key"])] = metric

        # Counterメトリクスを作成
        for counter_config in self.config.get("counters", []):
            name = str(counter_config["name"])
            if self._should_create_metric(name):
                counter_metric = Counter(
                    name,
                    str(counter_config["description"]),
                    list(counter_config["labels"]),
                    registry=self.registry,
                )
                self.metrics[str(counter_config["key"])] = counter_metric

        # Histogramメトリクスを作成
        for histogram_config in self.config.get("histograms", []):
            name = str(histogram_config["name"])
            if self._should_create_metric(name):
                histogram_metric = Histogram(
                    name,
                    str(histogram_config["description"]),
                    list(histogram_config["labels"]),
                    registry=self.registry,
                )
                self.metrics[str(histogram_config["key"])] = histogram_metric

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
        cls,
        registry: CollectorRegistry | None = None,
        app_config: ConfigProtocol | None = None,
    ) -> "MetricsFactory":
        """デフォルト設定でMetricsFactoryインスタンスを作成する.

        Args:
            registry: Prometheusレジストリ。Noneの場合はデフォルトレジストリを使用
            app_config: アプリケーション設定。メトリクス制御フラグを参照

        Returns:
            デフォルト設定のMetricsFactoryインスタンス
        """
        return cls(registry=registry, app_config=app_config)
