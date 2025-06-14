"""MetricsFactoryクラスのテストモジュール."""

from typing import Any
from unittest.mock import Mock, patch

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

from metrics_factory import MetricsFactory


class TestMetricsFactory:
    """MetricsFactoryクラスのテストケース."""

    def test_init_with_default_config(
        self, isolated_registry: CollectorRegistry
    ) -> None:
        """デフォルト設定での初期化をテストする."""
        factory = MetricsFactory(registry=isolated_registry)

        assert factory.config == MetricsFactory.DEFAULT_METRICS_CONFIG
        assert isinstance(factory.metrics, dict)
        assert len(factory.metrics) > 0

    def test_init_with_custom_config(
        self, isolated_registry: CollectorRegistry
    ) -> None:
        """カスタム設定での初期化をテストする."""
        custom_config = {
            "gauges": [
                {
                    "name": "test_gauge",
                    "description": "Test gauge",
                    "labels": ["label1"],
                    "key": "test_gauge",
                }
            ],
            "counters": [],
            "histograms": [],
        }

        with patch.object(MetricsFactory, "_create_metrics") as mock_create:
            factory = MetricsFactory(custom_config, registry=isolated_registry)

            assert factory.config == custom_config
            mock_create.assert_called_once()

    @patch("metrics_factory.Gauge")
    def test_create_gauge_metrics(
        self, mock_gauge: Mock, isolated_registry: CollectorRegistry
    ) -> None:
        """Gaugeメトリクス作成をテストする."""
        custom_config = {
            "gauges": [
                {
                    "name": "test_gauge",
                    "description": "Test gauge description",
                    "labels": ["symbol", "name"],
                    "key": "test_gauge_key",
                }
            ],
            "counters": [],
            "histograms": [],
        }

        mock_gauge_instance = Mock()
        mock_gauge.return_value = mock_gauge_instance

        factory = MetricsFactory(custom_config, registry=isolated_registry)

        # Gaugeが正しい引数で作成されたか確認
        mock_gauge.assert_called_once_with(
            "test_gauge",
            "Test gauge description",
            ["symbol", "name"],
            registry=isolated_registry,
        )

        # メトリクスが正しく保存されたか確認
        assert factory.metrics["test_gauge_key"] == mock_gauge_instance

    @patch("metrics_factory.Counter")
    def test_create_counter_metrics(
        self, mock_counter: Mock, isolated_registry: CollectorRegistry
    ) -> None:
        """Counterメトリクス作成をテストする."""
        custom_config = {
            "gauges": [],
            "counters": [
                {
                    "name": "test_counter",
                    "description": "Test counter description",
                    "labels": ["error_type"],
                    "key": "test_counter_key",
                }
            ],
            "histograms": [],
        }

        mock_counter_instance = Mock()
        mock_counter.return_value = mock_counter_instance

        factory = MetricsFactory(custom_config, registry=isolated_registry)

        # Counterが正しい引数で作成されたか確認
        mock_counter.assert_called_once_with(
            "test_counter",
            "Test counter description",
            ["error_type"],
            registry=isolated_registry,
        )

        # メトリクスが正しく保存されたか確認
        assert factory.metrics["test_counter_key"] == mock_counter_instance

    @patch("metrics_factory.Histogram")
    def test_create_histogram_metrics(
        self, mock_histogram: Mock, isolated_registry: CollectorRegistry
    ) -> None:
        """Histogramメトリクス作成をテストする."""
        custom_config = {
            "gauges": [],
            "counters": [],
            "histograms": [
                {
                    "name": "test_histogram",
                    "description": "Test histogram description",
                    "labels": ["operation"],
                    "key": "test_histogram_key",
                }
            ],
        }

        mock_histogram_instance = Mock()
        mock_histogram.return_value = mock_histogram_instance

        factory = MetricsFactory(custom_config, registry=isolated_registry)

        # Histogramが正しい引数で作成されたか確認
        mock_histogram.assert_called_once_with(
            "test_histogram",
            "Test histogram description",
            ["operation"],
            registry=isolated_registry,
        )

        # メトリクスが正しく保存されたか確認
        assert factory.metrics["test_histogram_key"] == mock_histogram_instance

    def test_get_metric_existing(self, isolated_registry: CollectorRegistry) -> None:
        """存在するメトリクスの取得をテストする."""
        factory = MetricsFactory(registry=isolated_registry)

        # 統一メトリクスキーを使用（DEFAULT_METRICS_CONFIGから）
        metric = factory.get_metric("financial_price")
        assert metric is not None
        assert isinstance(metric, Gauge)

    def test_get_metric_non_existing(
        self, isolated_registry: CollectorRegistry
    ) -> None:
        """存在しないメトリクスの取得をテストする."""
        factory = MetricsFactory(registry=isolated_registry)

        metric = factory.get_metric("non_existing_metric")
        assert metric is None

    def test_get_all_metrics(self, isolated_registry: CollectorRegistry) -> None:
        """全メトリクス取得をテストする."""
        factory = MetricsFactory(registry=isolated_registry)

        all_metrics = factory.get_all_metrics()
        assert isinstance(all_metrics, dict)
        assert len(all_metrics) > 0

        # DEFAULT_METRICS_CONFIGの統一メトリクスが含まれているか確認
        assert "financial_price" in all_metrics
        assert "financial_fetch_errors" in all_metrics

    def test_create_default_classmethod(
        self, isolated_registry: CollectorRegistry
    ) -> None:
        """create_defaultクラスメソッドをテストする."""
        factory = MetricsFactory.create_default(registry=isolated_registry)

        assert isinstance(factory, MetricsFactory)
        assert factory.config == MetricsFactory.DEFAULT_METRICS_CONFIG

    def test_default_metrics_config_structure(self) -> None:
        """デフォルトメトリクス設定の構造をテストする."""
        config = MetricsFactory.DEFAULT_METRICS_CONFIG

        assert "gauges" in config
        assert "counters" in config
        assert "histograms" in config

        assert isinstance(config["gauges"], list)
        assert isinstance(config["counters"], list)
        assert isinstance(config["histograms"], list)

        # 各メトリクス設定に必要なフィールドがあるか確認
        for gauge_config in config["gauges"]:
            assert "name" in gauge_config
            assert "description" in gauge_config
            assert "labels" in gauge_config
            assert "key" in gauge_config

    def test_metrics_creation_with_all_types(
        self, isolated_registry: CollectorRegistry
    ) -> None:
        """全種類のメトリクス作成をテストする."""
        # デフォルト設定には全種類のメトリクスが含まれている
        factory = MetricsFactory(registry=isolated_registry)

        # 各種類のメトリクスが作成されているか確認
        has_gauge = any(
            isinstance(metric, Gauge) for metric in factory.metrics.values()
        )
        has_counter = any(
            isinstance(metric, Counter) for metric in factory.metrics.values()
        )
        has_histogram = any(
            isinstance(metric, Histogram) for metric in factory.metrics.values()
        )

        assert has_gauge, "Gaugeメトリクスが作成されていません"
        assert has_counter, "Counterメトリクスが作成されていません"
        assert has_histogram, "Histogramメトリクスが作成されていません"

    def test_empty_config_sections(self, isolated_registry: CollectorRegistry) -> None:
        """空の設定セクションでの動作をテストする."""
        empty_config: dict[str, list[dict[str, Any]]] = {
            "gauges": [],
            "counters": [],
            "histograms": [],
        }

        factory = MetricsFactory(empty_config, registry=isolated_registry)

        assert len(factory.metrics) == 0
        assert factory.get_all_metrics() == {}

    def test_missing_config_sections(
        self, isolated_registry: CollectorRegistry
    ) -> None:
        """設定セクションが欠けている場合の動作をテストする."""
        partial_config = {
            "gauges": [
                {
                    "name": "test_gauge",
                    "description": "Test",
                    "labels": [],
                    "key": "test",
                }
            ]
            # countersとhistogramsセクションが欠けている
        }

        # 例外が発生せずに処理されることを確認
        factory = MetricsFactory(partial_config, registry=isolated_registry)
        assert len(factory.metrics) == 1
        assert "test" in factory.metrics

    def test_clear_all_metrics(self, isolated_registry: CollectorRegistry) -> None:
        """全メトリクスクリア機能のテスト."""
        factory = MetricsFactory(registry=isolated_registry)

        # いくつかのメトリクスに値を設定（統一メトリクス名を使用）
        financial_price = factory.get_metric("financial_price")
        financial_volume = factory.get_metric("financial_volume")

        if financial_price and isinstance(financial_price, Gauge):
            financial_price.labels(
                symbol="AAPL",
                name="Apple Inc.",
                currency="USD",
                exchange="NASDAQ",
                asset_type="stock",
            ).set(150.0)
        if financial_volume and isinstance(financial_volume, Gauge):
            financial_volume.labels(
                symbol="AAPL", name="Apple Inc.", exchange="NASDAQ", asset_type="stock"
            ).set(1000000)

        # メトリクスが設定されていることを確認
        metrics_before = factory.get_all_metrics()
        assert len(metrics_before) > 0

        # 全メトリクスをクリア
        factory.clear_all_metrics()

        # メトリクス自体は存在するが、値がクリアされていることを確認
        metrics_after = factory.get_all_metrics()
        assert len(metrics_after) == len(metrics_before)  # メトリクス定義は残る

        # 新しい値を設定できることを確認
        if financial_price and isinstance(financial_price, Gauge):
            financial_price.labels(
                symbol="GOOGL",
                name="Google",
                currency="USD",
                exchange="NASDAQ",
                asset_type="stock",
            ).set(100.0)
            # メトリクスが正常に動作することを確認
            assert financial_price is not None

    def test_unregister_all_metrics(self, isolated_registry: CollectorRegistry) -> None:
        """全メトリクスのレジストリからの削除機能のテスト."""
        factory = MetricsFactory(registry=isolated_registry)

        # 最初にメトリクスが存在することを確認
        initial_metrics = factory.get_all_metrics()
        assert len(initial_metrics) > 0

        # レジストリにメトリクスが登録されていることを確認
        registry_collectors_before = len(isolated_registry._collector_to_names)
        assert registry_collectors_before > 0

        # 全メトリクスをレジストリから削除
        factory.unregister_all_metrics()

        # メトリクス辞書がクリアされていることを確認
        assert len(factory.metrics) == 0

        # レジストリからメトリクスが削除されていることを確認
        registry_collectors_after = len(isolated_registry._collector_to_names)
        assert registry_collectors_after < registry_collectors_before

    def test_recreate_metrics(self, isolated_registry: CollectorRegistry) -> None:
        """メトリクス再作成機能のテスト."""
        factory = MetricsFactory(registry=isolated_registry)

        # 最初のメトリクス数を記録
        initial_metrics_count = len(factory.get_all_metrics())
        assert initial_metrics_count > 0

        # いくつかのメトリクスに値を設定
        financial_price = factory.get_metric("financial_price")
        if financial_price and isinstance(financial_price, Gauge):
            financial_price.labels(
                symbol="AAPL",
                name="Apple Inc.",
                currency="USD",
                exchange="NASDAQ",
                asset_type="stock",
            ).set(150.0)

        # メトリクスを再作成
        factory.recreate_metrics()

        # メトリクス数が元と同じであることを確認
        recreated_metrics = factory.get_all_metrics()
        assert len(recreated_metrics) == initial_metrics_count

        # 新しいメトリクスインスタンスが作成されていることを確認
        new_financial_price = factory.get_metric("financial_price")
        assert new_financial_price is not None
        assert isinstance(new_financial_price, Gauge)

        # 新しいメトリクスに値を設定できることを確認
        new_financial_price.labels(
            symbol="GOOGL",
            name="Google",
            currency="USD",
            exchange="NASDAQ",
            asset_type="stock",
        ).set(200.0)

    def test_unregister_already_unregistered_metric(
        self, isolated_registry: CollectorRegistry
    ) -> None:
        """既に削除されたメトリクスの削除試行のテスト."""
        factory = MetricsFactory(registry=isolated_registry)

        # 一度削除
        factory.unregister_all_metrics()

        # 再度削除しても例外が発生しないことを確認
        factory.unregister_all_metrics()

        # メトリクス辞書が空であることを確認
        assert len(factory.metrics) == 0
