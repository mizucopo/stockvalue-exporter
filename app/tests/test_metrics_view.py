"""MetricsViewクラスのテストモジュール."""

from collections.abc import Generator
from unittest.mock import MagicMock, Mock, patch

from flask import Flask
from prometheus_client import CollectorRegistry

from metrics_view import MetricsView


class TestMetricsView:
    """MetricsViewクラスのテストケース."""

    def test_update_prometheus_metrics(
        self, isolated_registry: CollectorRegistry
    ) -> None:
        """update_prometheus_metricsメトリクスメソッドをテストする."""
        from metrics_factory import MetricsFactory

        # 独立したレジストリでMetricsFactoryを作成
        metrics_factory = MetricsFactory(registry=isolated_registry)

        mock_app = Mock()
        mock_app.metrics_factory = metrics_factory

        # モック株価データ
        stock_data = {
            "AAPL": {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "currency": "USD",
                "exchange": "NASDAQ",
                "current_price": 150.0,
                "volume": 1000000,
                "market_cap": 2500000000000,
                "pe_ratio": 25.5,
                "dividend_yield": 0.005,
                "fifty_two_week_high": 180.0,
                "fifty_two_week_low": 120.0,
                "previous_close": 148.0,
                "price_change": 2.0,
                "price_change_percent": 1.35,
                "timestamp": 1638360000,
            }
        }

        metrics_view = MetricsView(app_instance=mock_app)
        metrics_view.update_prometheus_metrics(stock_data)

        # メトリクスが作成されたか確認
        assert len(metrics_factory.metrics) > 0

    def test_update_prometheus_metrics_with_exception(
        self, isolated_registry: CollectorRegistry
    ) -> None:
        """メトリクス更新時の例外処理をテストする."""
        from metrics_factory import MetricsFactory

        mock_app = Mock()

        # 独立したレジストリでMetricsFactoryを作成
        MetricsFactory(registry=isolated_registry)

        # メトリクスファクトリーで例外を発生させる
        mock_metrics_factory = Mock()
        mock_error_metric = Mock()

        def get_metric_side_effect(metric_name: str) -> Mock | None:
            if "fetch_errors" in metric_name:
                return mock_error_metric
            else:
                raise Exception("Metric error")

        mock_metrics_factory.get_metric.side_effect = get_metric_side_effect

        stock_data = {
            "AAPL": {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "exchange": "NASDAQ",
            }
        }

        mock_app.metrics_factory = mock_metrics_factory
        metrics_view = MetricsView(app_instance=mock_app)
        with patch("metrics_view.logger") as mock_logger:
            # 例外が発生しても処理が継続することを確認
            metrics_view.update_prometheus_metrics(stock_data)

            # エラーログが出力されたか確認
            mock_logger.error.assert_called()

    def test_get_method_with_default_symbols(
        self, request_context: Generator[None], isolated_registry: CollectorRegistry
    ) -> None:
        """デフォルトシンボルでのgetメソッドをテストする."""
        from metrics_factory import MetricsFactory

        mock_app = Mock()
        mock_fetcher = Mock()
        mock_app.fetcher = mock_fetcher

        # モック株価データ
        mock_stock_data = {
            "AAPL": {"symbol": "AAPL", "current_price": 150.0},
        }
        mock_fetcher.get_stock_data.return_value = mock_stock_data

        # 独立したレジストリでMetricsFactoryを作成
        metrics_factory = MetricsFactory(registry=isolated_registry)
        mock_app.metrics_factory = metrics_factory

        metrics_view = MetricsView(app_instance=mock_app)

        with patch("base_view.request") as mock_request:
            with patch("metrics_view.generate_latest") as mock_generate:
                mock_args = MagicMock()
                mock_args.getlist.return_value = []
                mock_args.get.return_value = ""
                mock_args.__contains__.return_value = False  # No symbols parameter
                mock_request.args = mock_args
                mock_generate.return_value = b"# Prometheus metrics"

                # update_prometheus_metricsをモック
                with patch.object(
                    metrics_view, "update_prometheus_metrics"
                ) as mock_update:
                    result = metrics_view.get()

                    # デフォルトシンボルで呼ばれたか確認
                    mock_fetcher.get_stock_data.assert_called_once_with(
                        [
                            "AAPL",
                            "GOOGL",
                            "MSFT",
                            "TSLA",
                            "^GSPC",
                            "^NDX",
                            "998405.T",
                            "^N225",
                            "BTC-USD",
                        ]
                    )
                    mock_update.assert_called_once_with(mock_stock_data)

                    # レスポンスを確認
                    assert result[0] == "# Prometheus metrics"
                    assert result[1] == 200
                    assert result[2]["Content-Type"] == "text/plain; charset=utf-8"

    def test_get_method_with_custom_symbols(
        self, request_context: Generator[None], isolated_registry: CollectorRegistry
    ) -> None:
        """カスタムシンボルでのgetメソッドをテストする."""
        mock_app = Mock()
        mock_fetcher = Mock()
        mock_app.fetcher = mock_fetcher
        mock_fetcher.get_stock_data.return_value = {}

        metrics_view = MetricsView(app_instance=mock_app)

        with patch("base_view.request") as mock_request:
            with patch("metrics_view.generate_latest") as mock_generate:
                mock_args = MagicMock()
                mock_args.getlist.return_value = ["NVDA,AMD"]
                mock_args.get.return_value = "NVDA,AMD"
                mock_args.__contains__.return_value = True
                mock_request.args = mock_args
                mock_generate.return_value = b"# Metrics"

                with patch.object(metrics_view, "update_prometheus_metrics"):
                    metrics_view.get()

                    mock_fetcher.get_stock_data.assert_called_once_with(["NVDA", "AMD"])

    def test_get_method_with_array_symbols(
        self, request_context: Generator[None], isolated_registry: CollectorRegistry
    ) -> None:
        """配列シンボルでのgetメソッドをテストする."""
        mock_app = Mock()
        mock_fetcher = Mock()
        mock_app.fetcher = mock_fetcher
        mock_fetcher.get_stock_data.return_value = {}

        metrics_view = MetricsView(app_instance=mock_app)

        with patch("base_view.request") as mock_request:
            with patch("metrics_view.generate_latest") as mock_generate:
                mock_args = MagicMock()
                mock_args.getlist.return_value = ["TSLA", "META"]
                mock_args.__contains__.return_value = True
                mock_request.args = mock_args
                mock_generate.return_value = b"# Metrics"

                with patch.object(metrics_view, "update_prometheus_metrics"):
                    metrics_view.get()

                    mock_fetcher.get_stock_data.assert_called_once_with(
                        ["TSLA", "META"]
                    )

    def test_get_method_with_exception(
        self, request_context: Generator[None], isolated_registry: CollectorRegistry
    ) -> None:
        """getメソッドでの例外処理をテストする."""
        mock_app = Mock()
        mock_fetcher = Mock()
        mock_app.fetcher = mock_fetcher
        mock_fetcher.get_stock_data.side_effect = Exception("Fetch error")

        metrics_view = MetricsView(app_instance=mock_app)

        with patch("base_view.request") as mock_request:
            with patch("metrics_view.generate_latest") as mock_generate:
                with patch("metrics_view.logger") as mock_logger:
                    mock_args = MagicMock()
                    mock_args.getlist.return_value = ["AAPL"]
                    mock_args.__contains__.return_value = True
                    mock_request.args = mock_args
                    mock_generate.return_value = b"# Error metrics"

                    result = metrics_view.get()

                    # エラーログが出力されたか確認
                    mock_logger.error.assert_called()

                    # エラーレスポンスを確認
                    assert result[1] == 500

    def test_get_method_with_mixed_parameters(
        self, request_context: Generator[None], isolated_registry: CollectorRegistry
    ) -> None:
        """混合パラメータでのgetメソッドをテストする."""
        mock_app = Mock()
        mock_fetcher = Mock()
        mock_app.fetcher = mock_fetcher
        mock_fetcher.get_stock_data.return_value = {}

        metrics_view = MetricsView(app_instance=mock_app)

        with patch("base_view.request") as mock_request:
            with patch("metrics_view.generate_latest") as mock_generate:
                mock_args = MagicMock()
                # カンマ区切りと配列の混合
                mock_args.getlist.return_value = ["AAPL,GOOGL", "MSFT"]
                mock_args.__contains__.return_value = True
                mock_request.args = mock_args
                mock_generate.return_value = b"# Metrics"

                with patch.object(metrics_view, "update_prometheus_metrics"):
                    metrics_view.get()

                    # 重複を除去して順序を保持した結果を期待
                    mock_fetcher.get_stock_data.assert_called_once_with(
                        ["AAPL", "GOOGL", "MSFT"]
                    )

    def test_get_method_with_duplicate_symbols(
        self, request_context: Generator[None], isolated_registry: CollectorRegistry
    ) -> None:
        """重複シンボルでのgetメソッドをテストする."""
        mock_app = Mock()
        mock_fetcher = Mock()
        mock_app.fetcher = mock_fetcher
        mock_fetcher.get_stock_data.return_value = {}

        metrics_view = MetricsView(app_instance=mock_app)

        with patch("base_view.request") as mock_request:
            with patch("metrics_view.generate_latest") as mock_generate:
                mock_args = MagicMock()
                # 重複したシンボルを含む
                mock_args.getlist.return_value = ["AAPL,GOOGL,AAPL", "GOOGL"]
                mock_args.__contains__.return_value = True
                mock_request.args = mock_args
                mock_generate.return_value = b"# Metrics"

                with patch.object(metrics_view, "update_prometheus_metrics"):
                    metrics_view.get()

                    # 重複を除去して順序を保持した結果を期待
                    mock_fetcher.get_stock_data.assert_called_once_with(
                        ["AAPL", "GOOGL"]
                    )

    def test_inheritance_from_base_view(self) -> None:
        """BaseViewからの継承をテストする."""
        from base_view import BaseView

        assert issubclass(MetricsView, BaseView)

    def test_get_method_with_clear_parameter(
        self, app: Flask, isolated_registry: CollectorRegistry
    ) -> None:
        """clearパラメータ付きでのメトリクス取得をテストする."""
        with app.test_request_context("/?symbols=AAPL&clear=true"):
            with patch("config.config.AUTO_CLEAR_METRICS", False):
                # MockアプリケーションにfetcherAttributeを追加
                mock_app = Mock()
                mock_app.fetcher.get_stock_data.return_value = {
                    "AAPL": {
                        "symbol": "AAPL",
                        "name": "Apple Inc.",
                        "current_price": 150.0,
                        "currency": "USD",
                        "exchange": "NASDAQ",
                        "volume": 1000000,
                        "market_cap": 2500000000000,
                        "pe_ratio": 25.5,
                        "dividend_yield": 0.005,
                        "fifty_two_week_high": 180.0,
                        "fifty_two_week_low": 120.0,
                        "previous_close": 148.0,
                        "price_change": 2.0,
                        "price_change_percent": 1.35,
                        "timestamp": 1638360000,
                    }
                }

                view = MetricsView(app_instance=mock_app)

                with patch.object(
                    view.app.metrics_factory, "clear_all_metrics"
                ) as mock_clear:
                    response, status_code, headers = view.get()

                    # メトリクスクリアが呼ばれたことを確認
                    mock_clear.assert_called_once()

                    assert status_code == 200
                    assert headers["Content-Type"] == "text/plain; charset=utf-8"

    def test_get_method_with_auto_clear_config(
        self, app: Flask, isolated_registry: CollectorRegistry
    ) -> None:
        """AUTO_CLEAR_METRICS設定でのメトリクス取得をテストする."""
        with app.test_request_context("/?symbols=AAPL"):
            with patch("config.config.AUTO_CLEAR_METRICS", True):  # 自動クリア有効
                # MockアプリケーションにfetcherAttributeを追加
                mock_app = Mock()
                mock_app.fetcher.get_stock_data.return_value = {
                    "AAPL": {
                        "symbol": "AAPL",
                        "name": "Apple Inc.",
                        "current_price": 150.0,
                        "currency": "USD",
                        "exchange": "NASDAQ",
                        "volume": 1000000,
                        "market_cap": 2500000000000,
                        "pe_ratio": 25.5,
                        "dividend_yield": 0.005,
                        "fifty_two_week_high": 180.0,
                        "fifty_two_week_low": 120.0,
                        "previous_close": 148.0,
                        "price_change": 2.0,
                        "price_change_percent": 1.35,
                        "timestamp": 1638360000,
                    }
                }

                view = MetricsView(app_instance=mock_app)

                with patch.object(
                    view.app.metrics_factory, "clear_all_metrics"
                ) as mock_clear:
                    response, status_code, headers = view.get()

                    # 自動クリアが呼ばれたことを確認
                    mock_clear.assert_called_once()

                    assert status_code == 200
                    assert headers["Content-Type"] == "text/plain; charset=utf-8"

    def test_get_method_without_clear(
        self, app: Flask, isolated_registry: CollectorRegistry
    ) -> None:
        """クリアパラメータなしでのメトリクス取得をテストする."""
        with app.test_request_context("/?symbols=AAPL"):
            with patch("config.config.AUTO_CLEAR_METRICS", False):  # 自動クリア無効
                # MockアプリケーションにfetcherAttributeを追加
                mock_app = Mock()

                # 独立したレジストリでMetricsFactoryを作成
                from metrics_factory import MetricsFactory

                metrics_factory = MetricsFactory(registry=isolated_registry)
                mock_app.metrics_factory = metrics_factory

                mock_app.fetcher.get_stock_data.return_value = {
                    "AAPL": {
                        "symbol": "AAPL",
                        "name": "Apple Inc.",
                        "current_price": 150.0,
                        "currency": "USD",
                        "exchange": "NASDAQ",
                        "volume": 1000000,
                        "market_cap": 2500000000000,
                        "pe_ratio": 25.5,
                        "dividend_yield": 0.005,
                        "fifty_two_week_high": 180.0,
                        "fifty_two_week_low": 120.0,
                        "previous_close": 148.0,
                        "price_change": 2.0,
                        "price_change_percent": 1.35,
                        "timestamp": 1638360000,
                    }
                }

                view = MetricsView(app_instance=mock_app)

                with patch.object(
                    view.app.metrics_factory, "clear_all_metrics"
                ) as mock_clear:
                    response, status_code, headers = view.get()

                    # メトリクスクリアが呼ばれていないことを確認
                    mock_clear.assert_not_called()

                    assert status_code == 200
                    assert headers["Content-Type"] == "text/plain; charset=utf-8"
