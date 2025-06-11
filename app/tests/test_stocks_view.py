"""StocksViewクラスのテストモジュール."""

import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

import pytest

from stocks_view import StocksView


class TestStocksView:
    """StocksViewクラスのテストケース."""

    def test_get_method_with_default_symbols(self, app_context, request_context):
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
        
        with patch("main.app", mock_app):
            with patch("stocks_view.request") as mock_request:
                # URLパラメータなしの場合 - MagicMockを使用してcoroutineを回避
                mock_args = MagicMock()
                mock_args.getlist.return_value = []
                mock_args.get.return_value = "AAPL,GOOGL,MSFT,TSLA"
                mock_request.args = mock_args
                
                stocks_view = StocksView()
                response = stocks_view.get()
                
                # JSONレスポンスを確認
                assert response.status_code == 200
                assert response.content_type == "application/json"
                
                # レスポンスデータを確認
                data = json.loads(response.get_data(as_text=True))
                assert "timestamp" in data
                assert data["symbols"] == ["AAPL", "GOOGL", "MSFT", "TSLA"]
                assert data["data"] == mock_stock_data
                
                # fetcherが正しい引数で呼ばれたか確認
                mock_fetcher.get_stock_data.assert_called_once_with(["AAPL", "GOOGL", "MSFT", "TSLA"])

    def test_get_method_with_custom_symbols_comma_separated(self, app_context, request_context):
        """カンマ区切りのカスタムシンボルでのgetメソッドをテストする."""
        mock_app = Mock()
        mock_fetcher = Mock()
        mock_app.fetcher = mock_fetcher
        
        mock_stock_data = {
            "NVDA": {"symbol": "NVDA", "price": 800.0},
            "AMD": {"symbol": "AMD", "price": 120.0},
        }
        mock_fetcher.get_stock_data.return_value = mock_stock_data
        
        with patch("main.app", mock_app):
            with patch("stocks_view.request") as mock_request:
                mock_args = MagicMock()
                mock_args.getlist.return_value = []
                mock_args.get.return_value = "nvda,amd"
                mock_request.args = mock_args
                
                stocks_view = StocksView()
                response = stocks_view.get()
                
                data = json.loads(response.get_data(as_text=True))
                assert data["symbols"] == ["NVDA", "AMD"]
                assert data["data"] == mock_stock_data
                
                mock_fetcher.get_stock_data.assert_called_once_with(["NVDA", "AMD"])

    def test_get_method_with_array_parameters(self, app_context, request_context):
        """配列パラメータでのgetメソッドをテストする."""
        mock_app = Mock()
        mock_fetcher = Mock()
        mock_app.fetcher = mock_fetcher
        
        mock_stock_data = {
            "TSLA": {"symbol": "TSLA", "price": 200.0},
            "META": {"symbol": "META", "price": 300.0},
        }
        mock_fetcher.get_stock_data.return_value = mock_stock_data
        
        with patch("main.app", mock_app):
            with patch("stocks_view.request") as mock_request:
                mock_args = MagicMock()
                mock_args.getlist.return_value = ["tsla", "meta"]
                mock_request.args = mock_args
                
                stocks_view = StocksView()
                response = stocks_view.get()
                
                data = json.loads(response.get_data(as_text=True))
                assert data["symbols"] == ["TSLA", "META"]
                assert data["data"] == mock_stock_data
                
                mock_fetcher.get_stock_data.assert_called_once_with(["TSLA", "META"])

    def test_get_method_with_whitespace_symbols(self, app_context, request_context):
        """空白を含むシンボルでのgetメソッドをテストする."""
        mock_app = Mock()
        mock_fetcher = Mock()
        mock_app.fetcher = mock_fetcher
        
        mock_stock_data = {"MSFT": {"symbol": "MSFT", "price": 350.0}}
        mock_fetcher.get_stock_data.return_value = mock_stock_data
        
        with patch("main.app", mock_app):
            with patch("stocks_view.request") as mock_request:
                mock_args = MagicMock()
                mock_args.getlist.return_value = []
                mock_args.get.return_value = " msft , , "
                mock_request.args = mock_args
                
                stocks_view = StocksView()
                response = stocks_view.get()
                
                data = json.loads(response.get_data(as_text=True))
                assert data["symbols"] == ["MSFT"]
                
                mock_fetcher.get_stock_data.assert_called_once_with(["MSFT"])

    def test_inheritance_from_base_view(self):
        """BaseViewからの継承をテストする."""
        from base_view import BaseView
        
        assert issubclass(StocksView, BaseView)

    def test_timestamp_format(self, app_context, request_context):
        """タイムスタンプの形式をテストする."""
        mock_app = Mock()
        mock_fetcher = Mock()
        mock_app.fetcher = mock_fetcher
        mock_fetcher.get_stock_data.return_value = {}
        
        with patch("main.app", mock_app):
            with patch("stocks_view.request") as mock_request:
                mock_args = MagicMock()
                mock_args.getlist.return_value = []
                mock_args.get.return_value = "AAPL"
                mock_request.args = mock_args
                
                with patch("stocks_view.datetime") as mock_datetime:
                    mock_now = Mock()
                    mock_now.isoformat.return_value = "2023-12-01T10:30:00"
                    mock_datetime.now.return_value = mock_now
                    
                    stocks_view = StocksView()
                    response = stocks_view.get()
                    
                    data = json.loads(response.get_data(as_text=True))
                    assert data["timestamp"] == "2023-12-01T10:30:00"