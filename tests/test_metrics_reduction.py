"""メトリクス削減機能のテスト."""

from unittest.mock import Mock, patch

import pytest
from prometheus_client import CollectorRegistry

from src.config import Config
from src.metrics_factory import MetricsFactory


class TestMetricsReduction:
    """メトリクス削減機能のテストクラス."""

    def test_default_metrics_all_enabled(
        self, isolated_registry: CollectorRegistry
    ) -> None:
        """デフォルト設定で全メトリクスが作成されることをテストする."""
        with patch("src.metrics_factory.REGISTRY", isolated_registry):
            factory = MetricsFactory.create_default()

        assert factory.registry is isolated_registry

        # 統一メトリクス削減後の期待されるメトリクス数確認（9個）
        all_metrics = factory.get_all_metrics()
        assert len(all_metrics) == 9

        # デバッグ系メトリクスの存在確認
        assert "financial_fetch_duration" in all_metrics
        assert "financial_fetch_errors" in all_metrics

    @pytest.mark.parametrize(
        ("enable_debug_metrics", "expected_count"),
        [
            pytest.param(True, 9, id="debug-enabled"),
            pytest.param(False, 7, id="debug-disabled"),
        ],
    )
    def test_unified_metrics_structure(
        self,
        isolated_registry: CollectorRegistry,
        enable_debug_metrics: bool,
        expected_count: int,
    ) -> None:
        """デバッグ設定ごとのメトリクス集合と件数をテストする."""
        mock_config = Mock(ENABLE_DEBUG_METRICS=enable_debug_metrics)
        factory = MetricsFactory.create_default(
            registry=isolated_registry, app_config=mock_config
        )
        all_metrics = factory.get_all_metrics()

        expected_metrics = {
            "financial_price",
            "financial_volume",
            "financial_market_cap",
            "financial_previous_close",
            "financial_price_change",
            "financial_price_change_percent",
            "financial_last_updated",
        }
        if enable_debug_metrics:
            expected_metrics.update(
                {"financial_fetch_duration", "financial_fetch_errors"}
            )

        assert set(all_metrics) == expected_metrics
        assert len(all_metrics) == expected_count

    def test_production_config_defaults(self) -> None:
        """本番環境設定のデフォルト値をテストする."""
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}, clear=True):
            config = Config()

            # 本番環境ではデバッグメトリクスがデフォルトで無効化
            assert not config.ENABLE_DEBUG_METRICS

    def test_development_config_defaults(self) -> None:
        """開発環境設定のデフォルト値をテストする."""
        with patch.dict("os.environ", {"ENVIRONMENT": "development"}, clear=True):
            config = Config()

            # 開発環境ではデバッグメトリクスがデフォルトで有効
            assert config.ENABLE_DEBUG_METRICS

    def test_config_override_with_env_vars(self) -> None:
        """環境変数による設定オーバーライドをテストする."""
        with patch.dict(
            "os.environ",
            {
                "ENVIRONMENT": "production",
                "ENABLE_DEBUG_METRICS": "true",
            },
            clear=True,
        ):
            config = Config()

            # 環境変数でオーバーライドされることを確認
            assert config.ENABLE_DEBUG_METRICS
