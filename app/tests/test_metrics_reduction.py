"""メトリクス削減機能のテスト."""

from unittest.mock import Mock, patch

from prometheus_client import CollectorRegistry

from config import Config
from metrics_factory import MetricsFactory


class TestMetricsReduction:
    """メトリクス削減機能のテストクラス."""

    def test_default_metrics_all_enabled(self):
        """デフォルト設定で全メトリクスが作成されることをテストする."""
        factory = MetricsFactory.create_default()

        # 全43個のメトリクスが作成されることを確認
        all_metrics = factory.get_all_metrics()
        assert len(all_metrics) == 43

        # 52週系メトリクスの存在確認
        assert "stock_52week_high" in all_metrics
        assert "forex_52week_high" in all_metrics

        # デバッグ系メトリクスの存在確認
        assert "stock_fetch_duration" in all_metrics
        assert "stock_fetch_errors" in all_metrics

    def test_range_metrics_disabled(self):
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

        # 他のメトリクスは残っていることを確認
        assert "stock_price" in all_metrics
        assert "stock_fetch_duration" in all_metrics

        # 削減効果を確認（43 - 8 = 35個）
        assert len(all_metrics) == 35

    def test_debug_metrics_disabled(self):
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

        # デバッグ系メトリクス（8個）が削除されることを確認
        debug_metrics = [
            "stock_fetch_duration",
            "stock_fetch_errors",
            "forex_fetch_duration",
            "forex_fetch_errors",
            "index_fetch_duration",
            "index_fetch_errors",
            "crypto_fetch_duration",
            "crypto_fetch_errors",
        ]

        for metric_key in debug_metrics:
            assert metric_key not in all_metrics

        # 52週系メトリクスは残っていることを確認
        assert "stock_52week_high" in all_metrics
        assert "forex_52week_high" in all_metrics

        # 削減効果を確認（43 - 8 = 35個）
        assert len(all_metrics) == 35

    def test_both_metrics_disabled(self):
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

        # 最大削減効果を確認（43 - 16 = 27個）
        assert len(all_metrics) == 27

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

        # コアメトリクスは残っていることを確認
        core_metrics = [
            "stock_price",
            "stock_volume",
            "stock_market_cap",
            "forex_rate",
            "index_value",
            "crypto_price",
        ]

        for metric_key in core_metrics:
            assert metric_key in all_metrics

    def test_production_config_defaults(self):
        """本番環境設定のデフォルト値をテストする."""
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            config = Config()

            # 本番環境では削減系メトリクスがデフォルトで無効
            assert config.ENABLE_RANGE_METRICS == False
            assert config.ENABLE_DEBUG_METRICS == False

    def test_development_config_defaults(self):
        """開発環境設定のデフォルト値をテストする."""
        with patch.dict("os.environ", {"ENVIRONMENT": "development"}, clear=True):
            config = Config()

            # 開発環境では全メトリクスがデフォルトで有効
            assert config.ENABLE_RANGE_METRICS == True
            assert config.ENABLE_DEBUG_METRICS == True

    def test_config_override_with_env_vars(self):
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
            assert config.ENABLE_RANGE_METRICS == True
            assert config.ENABLE_DEBUG_METRICS == True

    def test_metrics_reduction_impact(self):
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

        assert full_count == 43
        assert reduced_count == 27
        assert reduction == 16
        assert abs(reduction_percent - 37.2) < 0.1  # 約37%削減
