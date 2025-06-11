"""StockDataFetcherクラスのテストモジュール."""

import time
from unittest.mock import Mock, patch

import pytest

from stock_fetcher import StockDataFetcher


class TestStockDataFetcher:
    """StockDataFetcherクラスのテストケース."""

    def test_init(self):
        """StockDataFetcherクラスの初期化をテストする."""
        mock_duration = Mock()
        mock_errors = Mock()
        
        fetcher = StockDataFetcher(mock_duration, mock_errors)
        
        assert fetcher.cache == {}
        assert fetcher.cache_ttl == 300
        assert fetcher.stock_fetch_duration == mock_duration
        assert fetcher.stock_fetch_errors == mock_errors

    def test_init_with_none_parameters(self):
        """Noneパラメータでの初期化をテストする."""
        fetcher = StockDataFetcher()
        
        assert fetcher.cache == {}
        assert fetcher.cache_ttl == 300
        assert fetcher.stock_fetch_duration is None
        assert fetcher.stock_fetch_errors is None

    def test_is_cached_not_in_cache(self):
        """キャッシュにない場合のテストする."""
        fetcher = StockDataFetcher()
        
        result = fetcher._is_cached("AAPL")
        assert result is False

    def test_is_cached_expired(self):
        """期限切れキャッシュのテストする."""
        fetcher = StockDataFetcher()
        
        # 期限切れのキャッシュを設定
        old_timestamp = time.time() - 400  # 400秒前（TTL=300秒より古い）
        fetcher.cache["AAPL"] = {"timestamp": old_timestamp, "data": {}}
        
        result = fetcher._is_cached("AAPL")
        assert result is False

    def test_is_cached_valid(self):
        """有効なキャッシュのテストする."""
        fetcher = StockDataFetcher()
        
        # 有効なキャッシュを設定
        recent_timestamp = time.time() - 100  # 100秒前（TTL=300秒以内）
        fetcher.cache["AAPL"] = {"timestamp": recent_timestamp, "data": {}}
        
        result = fetcher._is_cached("AAPL")
        assert result is True

    def test_get_stock_data_from_cache(self):
        """キャッシュからのデータ取得をテストする."""
        fetcher = StockDataFetcher()
        
        # キャッシュデータを設定（実際の形式に合わせる）
        stock_data = {
            "symbol": "AAPL",
            "current_price": 150.0,
            "name": "Apple Inc.",
        }
        fetcher.cache["AAPL"] = {"data": stock_data, "timestamp": time.time()}
        
        with patch.object(fetcher, "_is_cached", return_value=True):
            result = fetcher.get_stock_data(["AAPL"])
            
            assert "AAPL" in result
            assert result["AAPL"] == stock_data

    @patch("stock_fetcher.yf")
    def test_get_stock_data_success(self, mock_yf):
        """株価データ取得成功をテストする."""
        fetcher = StockDataFetcher()
        
        # yfinanceのモックを設定
        mock_ticker = Mock()
        mock_info = {
            "symbol": "AAPL",
            "shortName": "Apple Inc.",
            "currency": "USD",
            "exchange": "NASDAQ",
            "regularMarketPrice": 150.0,
            "regularMarketVolume": 1000000,
            "marketCap": 2500000000000,
            "trailingPE": 25.5,
            "dividendYield": 0.005,
            "fiftyTwoWeekHigh": 180.0,
            "fiftyTwoWeekLow": 120.0,
            "regularMarketPreviousClose": 148.0,
        }
        mock_ticker.info = mock_info
        mock_yf.Ticker.return_value = mock_ticker
        
        with patch("time.time", return_value=1638360000):
            result = fetcher.get_stock_data(["AAPL"])
            
            assert "AAPL" in result
            stock_data = result["AAPL"]
            assert stock_data["symbol"] == "AAPL"
            assert stock_data["name"] == "Apple Inc."
            assert stock_data["current_price"] == 150.0
            assert stock_data["price_change"] == 2.0  # 150 - 148
            assert stock_data["price_change_percent"] == pytest.approx(1.351, rel=1e-2)

    @patch("stock_fetcher.yf")
    def test_get_stock_data_exception(self, mock_yf):
        """株価データ取得時の例外をテストする."""
        mock_duration = Mock()
        mock_errors = Mock()
        fetcher = StockDataFetcher(mock_duration, mock_errors)
        
        # yfinanceで例外を発生させる
        mock_yf.Ticker.side_effect = Exception("Network error")
        
        with patch("time.time", return_value=1638360000):
            result = fetcher.get_stock_data(["AAPL"])
            
            # エラー時のデフォルト値を確認
            assert "AAPL" in result
            stock_data = result["AAPL"]
            assert stock_data["symbol"] == "AAPL"
            assert stock_data["current_price"] == 0
            assert stock_data["name"] == "AAPL"
            
            # エラーメトリクスが記録されたか確認
            mock_errors.labels.assert_called()
            mock_errors.labels().inc.assert_called()

    @patch("stock_fetcher.yf")
    def test_get_stock_data_with_metrics(self, mock_yf):
        """メトリクス記録付きの株価データ取得をテストする."""
        mock_duration = Mock()
        mock_errors = Mock()
        fetcher = StockDataFetcher(mock_duration, mock_errors)
        
        # yfinanceのモックを設定
        mock_ticker = Mock()
        mock_ticker.info = {
            "symbol": "AAPL",
            "shortName": "Apple Inc.",
            "regularMarketPrice": 150.0,
            "regularMarketPreviousClose": 148.0,
        }
        mock_yf.Ticker.return_value = mock_ticker
        
        with patch("time.time") as mock_time:
            # 開始時間と終了時間を設定
            mock_time.side_effect = [1638360000, 1638360002, 1638360002, 1638360002]  # start, end, cache timestamp
            result = fetcher.get_stock_data(["AAPL"])
            
            # 実行時間メトリクスが記録されたか確認
            mock_duration.labels.assert_called_with(symbol="AAPL")
            mock_duration.labels().observe.assert_called_with(2)  # 2秒の実行時間

    def test_get_stock_data_multiple_symbols(self):
        """複数シンボルの株価データ取得をテストする."""
        fetcher = StockDataFetcher()
        
        with patch.object(fetcher, "_is_cached", return_value=False):
            with patch("stock_fetcher.yf") as mock_yf:
                # 複数のティッカーモックを設定
                def mock_ticker_factory(symbol):
                    mock_ticker = Mock()
                    mock_ticker.info = {
                        "symbol": symbol,
                        "shortName": f"{symbol} Inc.",
                        "regularMarketPrice": 100.0,
                        "regularMarketPreviousClose": 95.0,
                    }
                    return mock_ticker
                
                mock_yf.Ticker.side_effect = mock_ticker_factory
                
                with patch("time.time", return_value=1638360000):
                    result = fetcher.get_stock_data(["AAPL", "GOOGL"])
                    
                    assert len(result) == 2
                    assert "AAPL" in result
                    assert "GOOGL" in result
                    assert result["AAPL"]["symbol"] == "AAPL"
                    assert result["GOOGL"]["symbol"] == "GOOGL"

    def test_cache_storage(self):
        """キャッシュ保存をテストする."""
        fetcher = StockDataFetcher()
        
        with patch.object(fetcher, "_is_cached", return_value=False):
            with patch("stock_fetcher.yf") as mock_yf:
                mock_ticker = Mock()
                mock_ticker.info = {
                    "symbol": "AAPL",
                    "shortName": "Apple Inc.",
                    "regularMarketPrice": 150.0,
                    "regularMarketPreviousClose": 148.0,
                }
                mock_yf.Ticker.return_value = mock_ticker
                
                with patch("time.time", return_value=1638360000):
                    result = fetcher.get_stock_data(["AAPL"])
                    
                    # キャッシュに保存されたか確認
                    assert "AAPL" in fetcher.cache
                    assert "data" in fetcher.cache["AAPL"]
                    assert "timestamp" in fetcher.cache["AAPL"]
                    assert fetcher.cache["AAPL"]["data"]["symbol"] == "AAPL"
                    assert fetcher.cache["AAPL"]["timestamp"] == 1638360000