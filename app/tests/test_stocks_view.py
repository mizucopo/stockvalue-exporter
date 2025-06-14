"""StocksViewクラスのテストモジュール."""

import json
from collections.abc import Generator
from unittest.mock import MagicMock, Mock, patch

from flask import Flask
from prometheus_client import CollectorRegistry

from stocks_view import StocksView


class TestStocksView:
    """StocksViewクラスのテストケース."""

    def test_get_method_with_default_symbols(
        self, app_context: Flask, request_context: Generator[None]
    ) -> None:
        """デフォルトシンボルでのgetメソッドをテストする."""
        # モックアプリケーションインスタンスを作成
        mock_app = Mock()
        mock_fetcher = Mock()
        mock_app.fetcher = mock_fetcher

        # モック株価データ
        mock_stock_data = {
            "AAPL": {"symbol": "AAPL", "price": 150.0},
            "GOOGL": {"symbol": "GOOGL", "price": 2500.0},
        }
        mock_fetcher.get_stock_data.return_value = mock_stock_data

        stocks_view = StocksView(app_instance=mock_app)

        with patch("base_view.request") as mock_request:
            # URLパラメータなしの場合 - デフォルトシンボルを使用
            mock_args = MagicMock()
            mock_args.getlist.return_value = []
            mock_args.get.return_value = ""
            mock_args.__contains__.return_value = False
            mock_request.args = mock_args

            response = stocks_view.get()

            # JSONレスポンスを確認
            assert response.status_code == 200
            assert response.content_type == "application/json"

            # レスポンスデータを確認
            data = json.loads(response.get_data(as_text=True))
            assert "timestamp" in data
            assert data["symbols"] == [
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
            assert data["data"] == mock_stock_data

            # fetcherが正しい引数で呼ばれたか確認
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

    def test_get_method_with_custom_symbols_comma_separated(
        self, app_context: Flask, request_context: Generator[None]
    ) -> None:
        """カンマ区切りのカスタムシンボルでのgetメソッドをテストする."""
        mock_app = Mock()
        mock_fetcher = Mock()
        mock_app.fetcher = mock_fetcher

        mock_stock_data = {
            "NVDA": {"symbol": "NVDA", "price": 800.0},
            "AMD": {"symbol": "AMD", "price": 120.0},
        }
        mock_fetcher.get_stock_data.return_value = mock_stock_data

        stocks_view = StocksView(app_instance=mock_app)

        with patch("base_view.request") as mock_request:
            mock_args = MagicMock()
            mock_args.getlist.return_value = ["nvda,amd"]
            mock_args.get.return_value = "nvda,amd"
            mock_args.__contains__.return_value = True
            mock_request.args = mock_args

            response = stocks_view.get()

            data = json.loads(response.get_data(as_text=True))
            assert data["symbols"] == ["NVDA", "AMD"]
            assert data["data"] == mock_stock_data

            mock_fetcher.get_stock_data.assert_called_once_with(["NVDA", "AMD"])

    def test_get_method_with_array_parameters(
        self,
        app_context: Flask,
        request_context: Generator[None],
        isolated_registry: CollectorRegistry,
    ) -> None:
        """配列パラメータでのgetメソッドをテストする."""
        mock_app = Mock()
        mock_fetcher = Mock()
        mock_app.fetcher = mock_fetcher

        mock_stock_data = {
            "TSLA": {"symbol": "TSLA", "price": 200.0},
            "META": {"symbol": "META", "price": 300.0},
        }
        mock_fetcher.get_stock_data.return_value = mock_stock_data

        # 独立したレジストリでMetricsFactoryを作成
        from metrics_factory import MetricsFactory

        metrics_factory = MetricsFactory(registry=isolated_registry)
        mock_app.metrics_factory = metrics_factory

        with patch("base_view.request") as mock_request:
            mock_args = MagicMock()
            mock_args.getlist.return_value = ["tsla", "meta"]
            mock_args.__contains__.return_value = True
            mock_request.args = mock_args

            stocks_view = StocksView(app_instance=mock_app)
            response = stocks_view.get()

            data = json.loads(response.get_data(as_text=True))
            assert data["symbols"] == ["TSLA", "META"]
            assert data["data"] == mock_stock_data

            mock_fetcher.get_stock_data.assert_called_once_with(["TSLA", "META"])

    def test_get_method_with_whitespace_symbols(
        self,
        app_context: Flask,
        request_context: Generator[None],
        isolated_registry: CollectorRegistry,
    ) -> None:
        """空白を含むシンボルでのgetメソッドをテストする."""
        mock_app = Mock()
        mock_fetcher = Mock()
        mock_app.fetcher = mock_fetcher

        mock_stock_data = {"MSFT": {"symbol": "MSFT", "price": 350.0}}
        mock_fetcher.get_stock_data.return_value = mock_stock_data

        # 独立したレジストリでMetricsFactoryを作成
        from metrics_factory import MetricsFactory

        metrics_factory = MetricsFactory(registry=isolated_registry)
        mock_app.metrics_factory = metrics_factory

        with patch("base_view.request") as mock_request:
            mock_args = MagicMock()
            mock_args.getlist.return_value = [" msft , , "]
            mock_args.get.return_value = " msft , , "
            mock_args.__contains__.return_value = True
            mock_request.args = mock_args

            stocks_view = StocksView(app_instance=mock_app)
            response = stocks_view.get()

            data = json.loads(response.get_data(as_text=True))
            assert data["symbols"] == ["MSFT"]

            mock_fetcher.get_stock_data.assert_called_once_with(["MSFT"])

    def test_get_method_with_mixed_parameters(
        self,
        app_context: Flask,
        request_context: Generator[None],
        isolated_registry: CollectorRegistry,
    ) -> None:
        """混合パラメータでのgetメソッドをテストする."""
        mock_app = Mock()
        mock_fetcher = Mock()
        mock_app.fetcher = mock_fetcher

        mock_stock_data = {
            "AAPL": {"symbol": "AAPL", "price": 150.0},
            "GOOGL": {"symbol": "GOOGL", "price": 2500.0},
            "MSFT": {"symbol": "MSFT", "price": 350.0},
        }
        mock_fetcher.get_stock_data.return_value = mock_stock_data

        # 独立したレジストリでMetricsFactoryを作成
        from metrics_factory import MetricsFactory

        metrics_factory = MetricsFactory(registry=isolated_registry)
        mock_app.metrics_factory = metrics_factory

        with patch("base_view.request") as mock_request:
            mock_args = MagicMock()
            # カンマ区切りと配列の混合
            mock_args.getlist.return_value = ["aapl,googl", "msft"]
            mock_args.__contains__.return_value = True
            mock_request.args = mock_args

            stocks_view = StocksView(app_instance=mock_app)
            response = stocks_view.get()

            data = json.loads(response.get_data(as_text=True))
            assert data["symbols"] == ["AAPL", "GOOGL", "MSFT"]
            assert data["data"] == mock_stock_data

            mock_fetcher.get_stock_data.assert_called_once_with(
                ["AAPL", "GOOGL", "MSFT"]
            )

    def test_get_method_with_duplicate_symbols(
        self,
        app_context: Flask,
        request_context: Generator[None],
        isolated_registry: CollectorRegistry,
    ) -> None:
        """重複シンボルでのgetメソッドをテストする."""
        mock_app = Mock()
        mock_fetcher = Mock()
        mock_app.fetcher = mock_fetcher

        mock_stock_data = {
            "AAPL": {"symbol": "AAPL", "price": 150.0},
            "GOOGL": {"symbol": "GOOGL", "price": 2500.0},
        }
        mock_fetcher.get_stock_data.return_value = mock_stock_data

        # 独立したレジストリでMetricsFactoryを作成
        from metrics_factory import MetricsFactory

        metrics_factory = MetricsFactory(registry=isolated_registry)
        mock_app.metrics_factory = metrics_factory

        with patch("base_view.request") as mock_request:
            mock_args = MagicMock()
            # 重複したシンボルを含む
            mock_args.getlist.return_value = ["aapl,googl,aapl", "googl"]
            mock_args.__contains__.return_value = True
            mock_request.args = mock_args

            stocks_view = StocksView(app_instance=mock_app)
            response = stocks_view.get()

            data = json.loads(response.get_data(as_text=True))
            # 重複を除去して順序を保持
            assert data["symbols"] == ["AAPL", "GOOGL"]
            assert data["data"] == mock_stock_data

            mock_fetcher.get_stock_data.assert_called_once_with(["AAPL", "GOOGL"])

    def test_inheritance_from_base_view(self) -> None:
        """BaseViewからの継承をテストする."""
        from base_view import BaseView

        assert issubclass(StocksView, BaseView)

    def test_timestamp_format(
        self,
        app_context: Flask,
        request_context: Generator[None],
        isolated_registry: CollectorRegistry,
    ) -> None:
        """タイムスタンプの形式をテストする."""
        mock_app = Mock()
        mock_fetcher = Mock()
        mock_app.fetcher = mock_fetcher
        mock_fetcher.get_stock_data.return_value = {}

        # 独立したレジストリでMetricsFactoryを作成
        from metrics_factory import MetricsFactory

        metrics_factory = MetricsFactory(registry=isolated_registry)
        mock_app.metrics_factory = metrics_factory

        with patch("base_view.request") as mock_request:
            mock_args = MagicMock()
            mock_args.getlist.return_value = ["AAPL"]
            mock_args.get.return_value = "AAPL"
            mock_args.__contains__.return_value = True
            mock_request.args = mock_args

            with patch("stocks_view.datetime") as mock_datetime:
                mock_now = Mock()
                mock_now.isoformat.return_value = "2023-12-01T10:30:00"
                mock_datetime.now.return_value = mock_now

                stocks_view = StocksView(app_instance=mock_app)
                response = stocks_view.get()

                data = json.loads(response.get_data(as_text=True))
                assert data["timestamp"] == "2023-12-01T10:30:00"
