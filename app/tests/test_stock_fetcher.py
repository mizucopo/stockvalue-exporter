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
        assert fetcher.cache_ttl == 600
        assert fetcher.stock_fetch_duration == mock_duration
        assert fetcher.stock_fetch_errors == mock_errors

    def test_init_with_none_parameters(self):
        """Noneパラメータでの初期化をテストする."""
        fetcher = StockDataFetcher()

        assert fetcher.cache == {}
        assert fetcher.cache_ttl == 600
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
        old_timestamp = time.time() - 700  # 700秒前（TTL=600秒より古い）
        fetcher.cache["AAPL"] = {"timestamp": old_timestamp, "data": {}}

        result = fetcher._is_cached("AAPL")
        assert result is False

    def test_is_cached_valid(self):
        """有効なキャッシュのテストする."""
        fetcher = StockDataFetcher()

        # 有効なキャッシュを設定
        recent_timestamp = time.time() - 100  # 100秒前（TTL=600秒以内）
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

    def test_is_forex_pair_true(self):
        """為替ペアの判定（True）をテストする."""
        fetcher = StockDataFetcher()

        assert fetcher._is_forex_pair("USDJPY=X") is True
        assert fetcher._is_forex_pair("EURJPY=X") is True
        assert fetcher._is_forex_pair("GBPJPY=X") is True

    def test_is_forex_pair_false(self):
        """為替ペアの判定（False）をテストする."""
        fetcher = StockDataFetcher()

        assert fetcher._is_forex_pair("AAPL") is False
        assert fetcher._is_forex_pair("GOOGL") is False
        assert fetcher._is_forex_pair("BRK-B") is False
        assert fetcher._is_forex_pair("5255.T") is False

    @patch("stock_fetcher.yf")
    def test_get_stock_data_forex_pair(self, mock_yf):
        """為替ペアのデータ取得をテストする."""
        fetcher = StockDataFetcher()

        # yfinanceのモックを設定（為替レート用）
        mock_ticker = Mock()
        mock_info = {
            "symbol": "USDJPY=X",
            "shortName": "USD/JPY",
            "regularMarketPrice": 143.898,
            "regularMarketPreviousClose": 144.484,
            "fiftyTwoWeekHigh": 161.942,
            "fiftyTwoWeekLow": 139.578,
            "exchange": "CCY",
        }
        mock_ticker.info = mock_info
        mock_yf.Ticker.return_value = mock_ticker

        with patch("time.time", return_value=1638360000):
            result = fetcher.get_stock_data(["USDJPY=X"])

            assert "USDJPY=X" in result
            forex_data = result["USDJPY=X"]
            assert forex_data["symbol"] == "USDJPY=X"
            assert forex_data["name"] == "USD/JPY"
            assert forex_data["current_price"] == 143.898
            assert forex_data["currency"] == "JPY"
            assert forex_data["exchange"] == "CCY"
            # 為替ペア特有の値（株式では使用されない値）
            assert forex_data["market_cap"] == 0
            assert forex_data["pe_ratio"] == 0
            assert forex_data["dividend_yield"] == 0
            assert forex_data["volume"] == 0

    @patch("stock_fetcher.yf")
    def test_get_stock_data_forex_error(self, mock_yf):
        """為替ペアのエラー時デフォルト値をテストする."""
        mock_errors = Mock()
        fetcher = StockDataFetcher(stock_fetch_errors=mock_errors)

        # yfinanceで例外を発生させる
        mock_yf.Ticker.side_effect = Exception("Network error")

        with patch("time.time", return_value=1638360000):
            result = fetcher.get_stock_data(["USDJPY=X"])

            # エラー時のデフォルト値を確認（為替ペア用）
            assert "USDJPY=X" in result
            forex_data = result["USDJPY=X"]
            assert forex_data["symbol"] == "USDJPY=X"
            assert forex_data["currency"] == "JPY"
            assert forex_data["exchange"] == "FX"
            assert forex_data["current_price"] == 0
            assert forex_data["market_cap"] == 0
            assert forex_data["pe_ratio"] == 0
            assert forex_data["dividend_yield"] == 0
            assert forex_data["volume"] == 0

    @patch("stock_fetcher.yf")
    def test_get_stock_data_mixed_symbols(self, mock_yf):
        """株式と為替ペアの混合シンボルをテストする."""
        fetcher = StockDataFetcher()

        def mock_ticker_side_effect(symbol):
            mock_ticker = Mock()
            if symbol == "AAPL":
                mock_ticker.info = {
                    "symbol": "AAPL",
                    "shortName": "Apple Inc.",
                    "regularMarketPrice": 150.0,
                    "regularMarketPreviousClose": 148.0,
                    "marketCap": 2500000000000,
                    "trailingPE": 25.5,
                    "dividendYield": 0.005,
                    "volume": 50000000,
                }
            elif symbol == "USDJPY=X":
                mock_ticker.info = {
                    "symbol": "USDJPY=X",
                    "shortName": "USD/JPY",
                    "regularMarketPrice": 143.898,
                    "regularMarketPreviousClose": 144.484,
                    "exchange": "CCY",
                }
            return mock_ticker

        mock_yf.Ticker.side_effect = mock_ticker_side_effect

        with patch("time.time", return_value=1638360000):
            result = fetcher.get_stock_data(["AAPL", "USDJPY=X"])

            # 株式データの確認
            assert "AAPL" in result
            stock_data = result["AAPL"]
            assert stock_data["market_cap"] == 2500000000000
            assert stock_data["pe_ratio"] == 25.5
            assert stock_data["dividend_yield"] == 0.005
            assert stock_data["volume"] == 50000000

            # 為替レートデータの確認
            assert "USDJPY=X" in result
            forex_data = result["USDJPY=X"]
            assert forex_data["market_cap"] == 0
            assert forex_data["pe_ratio"] == 0
            assert forex_data["dividend_yield"] == 0
            assert forex_data["volume"] == 0

    def test_is_index_true(self):
        """指数の判定（True）をテストする."""
        fetcher = StockDataFetcher()
        
        assert fetcher._is_index("^GSPC") is True
        assert fetcher._is_index("^NDX") is True
        assert fetcher._is_index("^N225") is True
        assert fetcher._is_index("998405.T") is True

    def test_is_index_false(self):
        """指数の判定（False）をテストする."""
        fetcher = StockDataFetcher()
        
        assert fetcher._is_index("AAPL") is False
        assert fetcher._is_index("GOOGL") is False
        assert fetcher._is_index("USDJPY=X") is False
        assert fetcher._is_index("BRK-B") is False
        assert fetcher._is_index("5255.T") is False  # 通常の日本株

    @patch("stock_fetcher.yf")
    def test_get_stock_data_index(self, mock_yf):
        """指数のデータ取得をテストする."""
        fetcher = StockDataFetcher()

        # yfinanceのモックを設定（指数用）
        mock_ticker = Mock()
        mock_info = {
            "symbol": "^GSPC",
            "shortName": "S&P 500",
            "regularMarketPrice": 6022.24,
            "regularMarketPreviousClose": 6038.81,
            "fiftyTwoWeekHigh": 6147.43,
            "fiftyTwoWeekLow": 4835.04,
            "volume": 2978585000,
        }
        mock_ticker.info = mock_info
        mock_yf.Ticker.return_value = mock_ticker

        with patch("time.time", return_value=1638360000):
            result = fetcher.get_stock_data(["^GSPC"])

            assert "^GSPC" in result
            index_data = result["^GSPC"]
            assert index_data["symbol"] == "^GSPC"
            assert index_data["name"] == "S&P 500"
            assert index_data["current_price"] == 6022.24
            assert index_data["currency"] == "USD"
            assert index_data["exchange"] == "INDEX"
            assert index_data["volume"] == 2978585000
            # 指数特有の値（株式では使用される値）
            assert index_data["market_cap"] == 0
            assert index_data["pe_ratio"] == 0
            assert index_data["dividend_yield"] == 0
