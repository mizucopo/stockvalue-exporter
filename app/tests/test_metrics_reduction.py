"""メトリクス削減機能のテスト."""

from unittest.mock import Mock, patch

from prometheus_client import CollectorRegistry

from config import Config
from metrics_factory import MetricsFactory


class TestMetricsReduction:
    """メトリクス削減機能のテストクラス."""

    def test_default_metrics_all_enabled(self) -> None:
        """デフォルト設定で全メトリクスが作成されることをテストする."""
        factory = MetricsFactory.create_default()

        # 統一メトリクス削減後の期待されるメトリクス数確認（9個）
        all_metrics = factory.get_all_metrics()
        assert len(all_metrics) == 9

        # デバッグ系メトリクスの存在確認
        assert "financial_fetch_duration" in all_metrics
        assert "financial_fetch_errors" in all_metrics

    def test_range_metrics_disabled(self) -> None:
        """ENABLE_RANGE_METRICS=Falseで52週系メトリクスが無効化されることをテストする."""
        # 独立したレジストリを使用
        registry = CollectorRegistry()

        # モック設定を作成
        mock_config = Mock()
        mock_config.ENABLE_RANGE_METRICS = False
        mock_config.ENABLE_DEBUG_METRICS = True

        factory = MetricsFactory.create_default(
            registry=registry, app_config=mock_config
        )
        all_metrics = factory.get_all_metrics()

        # 52週系メトリクス（8個）が削除されることを確認
        range_metrics = [
            "stock_52week_high",
            "stock_52week_low",
            "forex_52week_high",
            "forex_52week_low",
            "index_52week_high",
            "index_52week_low",
            "crypto_52week_high",
            "crypto_52week_low",
        ]

        for metric_key in range_metrics:
            assert metric_key not in all_metrics

        # 他のメトリクスは残っていることを確認（統一メトリクス）
        assert "financial_price" in all_metrics
        assert "financial_fetch_duration" in all_metrics

        # 削減効果を確認（統一メトリクスでの数）
        assert len(all_metrics) == 9  # 統一メトリクス後の期待値: 7 Gauge + 1 Counter + 1 Histogram

    def test_debug_metrics_disabled(self) -> None:
        """ENABLE_DEBUG_METRICS=Falseでデバッグ系メトリクスが無効化されることをテストする."""
        # 独立したレジストリを使用
        registry = CollectorRegistry()

        # モック設定を作成
        mock_config = Mock()
        mock_config.ENABLE_RANGE_METRICS = True
        mock_config.ENABLE_DEBUG_METRICS = False

        factory = MetricsFactory.create_default(
            registry=registry, app_config=mock_config
        )
        all_metrics = factory.get_all_metrics()

        # 統一メトリクスでデバッグ系メトリクス（Counter/Histogram）が削除されることを確認
        debug_metrics = [
            "financial_fetch_duration",
            "financial_fetch_errors",
        ]

        for metric_key in debug_metrics:
            assert metric_key not in all_metrics

        # 削減効果を確認（統一メトリクスでの数）
        assert len(all_metrics) == 7  # 7 Gauge のみ（Counter/Histogramがデバッグ系で削除）

    def test_both_metrics_disabled(self) -> None:
        """両方無効化で最大削減効果をテストする."""
        # 独立したレジストリを使用
        registry = CollectorRegistry()

        # モック設定を作成
        mock_config = Mock()
        mock_config.ENABLE_RANGE_METRICS = False
        mock_config.ENABLE_DEBUG_METRICS = False

        factory = MetricsFactory.create_default(
            registry=registry, app_config=mock_config
        )
        all_metrics = factory.get_all_metrics()

        # 最大削減効果を確認（統一メトリクス後）
        assert len(all_metrics) == 7  # 7 Gauge + 0 Counter + 0 Histogram（デバッグ系削除）

        # 削除対象メトリクスが全て削除されていることを確認
        deleted_metrics = [
            # 52週系（8個）
            "stock_52week_high",
            "stock_52week_low",
            "forex_52week_high",
            "forex_52week_low",
            "index_52week_high",
            "index_52week_low",
            "crypto_52week_high",
            "crypto_52week_low",
            # デバッグ系（8個）
            "stock_fetch_duration",
            "stock_fetch_errors",
            "forex_fetch_duration",
            "forex_fetch_errors",
            "index_fetch_duration",
            "index_fetch_errors",
            "crypto_fetch_duration",
            "crypto_fetch_errors",
        ]

        for metric_key in deleted_metrics:
            assert metric_key not in all_metrics

        # コアメトリクスは残っていることを確認（統一メトリクス名）
        core_metrics = [
            "financial_price",
            "financial_volume",
            "financial_market_cap",
            "financial_previous_close",
            "financial_price_change",
            "financial_price_change_percent",
            "financial_last_updated",
        ]

        for metric_key in core_metrics:
            assert metric_key in all_metrics

    def test_production_config_defaults(self) -> None:
        """本番環境設定のデフォルト値をテストする."""
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            config = Config()

            # 本番環境では削減系メトリクスがデフォルトで無効
            assert not config.ENABLE_RANGE_METRICS
            assert not config.ENABLE_DEBUG_METRICS

    def test_development_config_defaults(self) -> None:
        """開発環境設定のデフォルト値をテストする."""
        with patch.dict("os.environ", {"ENVIRONMENT": "development"}, clear=True):
            config = Config()

            # 開発環境では全メトリクスがデフォルトで有効
            assert config.ENABLE_RANGE_METRICS
            assert config.ENABLE_DEBUG_METRICS

    def test_config_override_with_env_vars(self) -> None:
        """環境変数による設定オーバーライドをテストする."""
        with patch.dict(
            "os.environ",
            {
                "ENVIRONMENT": "production",
                "ENABLE_RANGE_METRICS": "true",
                "ENABLE_DEBUG_METRICS": "true",
            },
        ):
            config = Config()

            # 環境変数でオーバーライドされることを確認
            assert config.ENABLE_RANGE_METRICS
            assert config.ENABLE_DEBUG_METRICS

    def test_metrics_reduction_impact(self) -> None:
        """メトリクス削減の効果を数値で確認する."""
        # フル設定用レジストリ
        full_registry = CollectorRegistry()
        full_config = Mock()
        full_config.ENABLE_RANGE_METRICS = True
        full_config.ENABLE_DEBUG_METRICS = True
        full_factory = MetricsFactory.create_default(
            registry=full_registry, app_config=full_config
        )
        full_count = len(full_factory.get_all_metrics())

        # 削減設定用レジストリ
        reduced_registry = CollectorRegistry()
        reduced_config = Mock()
        reduced_config.ENABLE_RANGE_METRICS = False
        reduced_config.ENABLE_DEBUG_METRICS = False
        reduced_factory = MetricsFactory.create_default(
            registry=reduced_registry, app_config=reduced_config
        )
        reduced_count = len(reduced_factory.get_all_metrics())

        # 削減効果を確認
        reduction = full_count - reduced_count
        reduction_percent = (reduction / full_count) * 100

        assert full_count == 9  # 統一メトリクス削減後: 7 Gauge + 1 Counter + 1 Histogram
        assert reduced_count == 7  # 最大削減後: 7 Gauge のみ（Counter/Histogramがデバッグ系で削除）
        assert reduction == 2
        assert abs(reduction_percent - 22.2) < 0.1  # 約22%削減
