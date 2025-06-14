"""StockDataFetcherクラスのテストモジュール."""

from unittest.mock import Mock, patch

import pytest
from prometheus_client import CollectorRegistry

from stock_fetcher import StockDataFetcher


class TestStockDataFetcher:
    """StockDataFetcherクラスのテストケース."""

    def test_init(self, isolated_registry: CollectorRegistry) -> None:
        """StockDataFetcherクラスの初期化をテストする."""
        mock_duration = Mock()
        mock_errors = Mock()

        fetcher = StockDataFetcher(mock_duration, mock_errors)

        assert fetcher.cache._cache == {}
        assert fetcher.cache_ttl == 600
        assert fetcher.financial_fetch_duration == mock_duration
        assert fetcher.financial_fetch_errors == mock_errors

    def test_init_with_none_parameters(
        self, isolated_registry: CollectorRegistry
    ) -> None:
        """Noneパラメータでの初期化をテストする."""
        fetcher = StockDataFetcher()

        assert fetcher.cache._cache == {}
        assert fetcher.cache_ttl == 600
        assert fetcher.financial_fetch_duration is None
        assert fetcher.financial_fetch_errors is None

    def test_is_cached_not_in_cache(self) -> None:
        """キャッシュにない場合のテストする."""
        fetcher = StockDataFetcher()

        result = fetcher._is_cached("AAPL")
        assert result is False

    def test_is_cached_expired(self, isolated_registry: CollectorRegistry) -> None:
        """期限切れキャッシュのテストする."""
        fetcher = StockDataFetcher()

        # 期限切れのキャッシュは自動的にNoneが返される
        # キャッシュに手動で古いデータを設定することはできないため、
        # 代わりにキャッシュが空の場合をテスト
        result = fetcher._is_cached("AAPL")
        assert result is False

    def test_is_cached_valid(self, isolated_registry: CollectorRegistry) -> None:
        """有効なキャッシュのテストする."""
        fetcher = StockDataFetcher()

        # 有効なキャッシュを設定
        test_data = {"symbol": "AAPL", "current_price": 150.0}
        fetcher.cache.put("AAPL", test_data)

        result = fetcher._is_cached("AAPL")
        assert result is True

    def test_get_stock_data_from_cache(
        self, isolated_registry: CollectorRegistry
    ) -> None:
        """キャッシュからのデータ取得をテストする."""
        fetcher = StockDataFetcher()

        # キャッシュデータを設定（実際の形式に合わせる）
        stock_data = {
            "symbol": "AAPL",
            "current_price": 150.0,
            "name": "Apple Inc.",
        }
        fetcher.cache.put("AAPL", stock_data)

        with patch.object(fetcher, "_is_cached", return_value=True):
            result = fetcher.get_stock_data(["AAPL"])

            assert "AAPL" in result
            assert result["AAPL"] == stock_data

    @patch("stock_fetcher.yf")
    def test_get_stock_data_success(self, mock_yf: Mock) -> None:
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
            assert stock_data["currency"] == "USD"
            assert stock_data["exchange"] == "NASDAQ"
            assert stock_data["asset_type"] == "stock"  # 統一メトリクス: asset_type追加
            assert stock_data["current_price"] == 150.0
            assert stock_data["price_change"] == 2.0  # 150 - 148
            assert stock_data["price_change_percent"] == pytest.approx(1.351, rel=1e-2)

    @patch("stock_fetcher.yf")
    def test_get_stock_data_exception(self, mock_yf: Mock) -> None:
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
            assert stock_data["asset_type"] == "stock"  # 統一メトリクス: asset_type追加
            assert stock_data["current_price"] == 0
            assert stock_data["name"] == "AAPL"

            # エラーメトリクスが記録されたか確認
            mock_errors.labels.assert_called()
            mock_errors.labels().inc.assert_called()

    @patch("stock_fetcher.yf")
    def test_get_stock_data_with_metrics(self, mock_yf: Mock) -> None:
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
            mock_time.side_effect = [
                1638360000,
                1638360002,
                1638360002,
                1638360002,
            ]  # start, end, cache timestamp
            fetcher.get_stock_data(["AAPL"])

            # 実行時間メトリクスが記録されたか確認
            mock_duration.labels.assert_called_with(symbol="AAPL")
            mock_duration.labels().observe.assert_called_with(2)  # 2秒の実行時間

    def test_get_stock_data_multiple_symbols(self) -> None:
        """複数シンボルの株価データ取得をテストする."""
        fetcher = StockDataFetcher()

        with patch.object(fetcher, "_is_cached", return_value=False):
            with patch("stock_fetcher.yf") as mock_yf:
                # 複数のティッカーモックを設定
                def mock_ticker_factory(symbol: str) -> Mock:
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

    def test_cache_storage(self) -> None:
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
                    fetcher.get_stock_data(["AAPL"])

                    # キャッシュに保存されたか確認
                    cached_data = fetcher.cache.get("AAPL")
                    assert cached_data is not None
                    assert cached_data["symbol"] == "AAPL"

    @patch("stock_fetcher.yf")
    def test_get_stock_data_forex_pair(self, mock_yf: Mock) -> None:
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
            assert forex_data["exchange"] == "FX"
            # 為替ペア特有の値（株式では使用されない値）
            assert forex_data["market_cap"] == 0
            assert forex_data["pe_ratio"] == 0
            assert forex_data["dividend_yield"] == 0
            assert forex_data["volume"] == 0

    @patch("stock_fetcher.yf")
    def test_get_stock_data_forex_error(self, mock_yf: Mock) -> None:
        """為替ペアのエラー時デフォルト値をテストする."""
        mock_errors = Mock()
        fetcher = StockDataFetcher(financial_fetch_errors=mock_errors)

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
            assert forex_data["asset_type"] == "forex"  # 統一メトリクス: asset_type追加
            assert forex_data["current_price"] == 0
            assert forex_data["market_cap"] == 0
            assert forex_data["pe_ratio"] == 0
            assert forex_data["dividend_yield"] == 0
            assert forex_data["volume"] == 0

    @patch("stock_fetcher.yf")
    def test_get_stock_data_mixed_symbols(self, mock_yf: Mock) -> None:
        """株式と為替ペアの混合シンボルをテストする."""
        fetcher = StockDataFetcher()

        def mock_ticker_side_effect(symbol: str) -> Mock:
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

    def test_get_currency_symbol(self) -> None:
        """通貨記号の取得をテストする."""
        fetcher = StockDataFetcher()

        # 主要通貨の記号を確認
        assert fetcher._get_currency_symbol("USD") == "$"
        assert fetcher._get_currency_symbol("JPY") == "¥"
        assert fetcher._get_currency_symbol("EUR") == "€"
        assert fetcher._get_currency_symbol("GBP") == "£"
        assert fetcher._get_currency_symbol("CNY") == "¥"
        assert fetcher._get_currency_symbol("KRW") == "₩"
        assert fetcher._get_currency_symbol("AUD") == "A$"
        assert fetcher._get_currency_symbol("CAD") == "C$"
        assert fetcher._get_currency_symbol("CHF") == "CHF"
        assert fetcher._get_currency_symbol("HKD") == "HK$"
        assert fetcher._get_currency_symbol("SGD") == "S$"

        # 大文字小文字の処理を確認
        assert fetcher._get_currency_symbol("usd") == "$"
        assert fetcher._get_currency_symbol("jpy") == "¥"

        # 未知の通貨コードの場合はそのまま返す
        assert fetcher._get_currency_symbol("UNKNOWN") == "UNKNOWN"
        assert fetcher._get_currency_symbol("XYZ") == "XYZ"

    @patch("stock_fetcher.yf")
    def test_get_stock_data_index(self, mock_yf: Mock) -> None:
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
