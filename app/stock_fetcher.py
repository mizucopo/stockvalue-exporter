"""株価データフェッチャーモジュール."""

import logging
import time
from typing import Any

import yfinance as yf
from prometheus_client import Counter, Histogram

from cache import LRUCache

logger = logging.getLogger(__name__)


class StockDataFetcher:
    """株価データを取得するクラス."""

    def __init__(
        self,
        stock_fetch_duration: Histogram | None = None,
        stock_fetch_errors: Counter | None = None,
    ) -> None:
        """株価データフェッチャーを初期化する.

        Args:
            stock_fetch_duration: フェッチ時間を計測するHistogramメトリクス
            stock_fetch_errors: エラー数を計測するCounterメトリクス
        """
        self.cache = LRUCache()
        self.stock_fetch_duration = stock_fetch_duration
        self.stock_fetch_errors = stock_fetch_errors

    def _is_forex_pair(self, symbol: str) -> bool:
        """シンボルが為替ペアかどうかを判定する.
        
        Args:
            symbol: 判定するシンボル
            
        Returns:
            為替ペアならTrue、そうでなければFalse
        """
        return symbol.endswith("=X")

    def _is_index(self, symbol: str) -> bool:
        """シンボルが株価指数かどうかを判定する.
        
        Args:
            symbol: 判定するシンボル
            
        Returns:
            指数ならTrue、そうでなければFalse
        """
        # ^で始まる指数（S&P500, NASDAQ100, 日経平均など）
        if symbol.startswith("^"):
            return True
        # 特定の日本の指数シンボル（TOPIX等）
        known_japanese_indices = ["998405.T"]
        if symbol in known_japanese_indices:
            return True
        return False

    def get_stock_data(self, symbols: list[str]) -> dict[str, Any]:
        """指定された銘柄の株価データまたは為替レートデータを取得する.

        Args:
            symbols: 取得する銘柄シンボルまたは為替ペアのリスト

        Returns:
            銘柄別の株価データまたは為替レートデータ辞書
        """
        results = {}

        for symbol in symbols:
            start_time = time.time()

            try:
                # キャッシュチェック
                cached_data = self.cache.get(symbol)
                if cached_data is not None:
                    results[symbol] = cached_data
                    continue

                # Yahoo Finance APIから株価データ取得
                ticker = yf.Ticker(symbol)
                info = ticker.info

                if not info:
                    raise ValueError(f"No data found for symbol: {symbol}")

                # 現在価格と前日終値の取得
                current_price = info.get(
                    "currentPrice", info.get("regularMarketPrice", 0)
                )
                previous_close = info.get(
                    "previousClose", info.get("regularMarketPreviousClose", 0)
                )

                # 前日比計算
                price_change = current_price - previous_close if previous_close else 0
                price_change_percent = (
                    (price_change / previous_close * 100) if previous_close else 0
                )

                # シンボルタイプによってデータ構造を調整
                is_forex = self._is_forex_pair(symbol)
                is_index = self._is_index(symbol)
                
                # 通貨の設定
                if symbol == "USDJPY=X":
                    currency = "JPY"
                elif symbol in ["^N225", "998405.T"]:  # 日本の指数
                    currency = "JPY"
                else:
                    currency = info.get("currency", "USD")
                
                # 取引所の設定
                if is_forex:
                    exchange = "FX"
                elif is_index:
                    exchange = "INDEX"
                else:
                    exchange = info.get("exchange", "Unknown")

                stock_data = {
                    "symbol": symbol,
                    "name": info.get("longName", info.get("shortName", symbol)),
                    "currency": currency,
                    "exchange": exchange,
                    "current_price": current_price,
                    "previous_close": previous_close,
                    "price_change": price_change,
                    "price_change_percent": price_change_percent,
                    "volume": 0 if is_forex else info.get("volume", info.get("regularMarketVolume", 0)),
                    "market_cap": 0 if (is_forex or is_index) else info.get("marketCap", 0),
                    "pe_ratio": 0 if (is_forex or is_index) else info.get("trailingPE", 0),
                    "dividend_yield": 0 if (is_forex or is_index) else info.get("dividendYield", 0),
                    "fifty_two_week_high": info.get("fiftyTwoWeekHigh", 0),
                    "fifty_two_week_low": info.get("fiftyTwoWeekLow", 0),
                    "timestamp": time.time(),
                }

                # キャッシュに保存
                self.cache.put(symbol, stock_data)

                results[symbol] = stock_data

                # メトリクス記録
                if self.stock_fetch_duration:
                    duration = time.time() - start_time
                    self.stock_fetch_duration.labels(symbol=symbol).observe(duration)

                logger.info(
                    f"Successfully fetched data for {symbol}: ${stock_data['current_price']} (${stock_data['price_change']:+.2f}, {stock_data['price_change_percent']:+.2f}%)"
                )

            except Exception as e:
                logger.error(f"Error fetching data for {symbol}: {e}")

                # エラーメトリクス記録
                if self.stock_fetch_errors:
                    self.stock_fetch_errors.labels(
                        symbol=symbol, error_type=type(e).__name__
                    ).inc()

                # エラー時のデフォルト値（シンボルタイプによって調整）
                is_forex_error = self._is_forex_pair(symbol)
                is_index_error = self._is_index(symbol)
                
                # エラー時の通貨設定
                if symbol == "USDJPY=X":
                    error_currency = "JPY"
                elif symbol in ["^N225", "998405.T"]:
                    error_currency = "JPY"
                else:
                    error_currency = "USD"
                
                # エラー時の取引所設定
                if is_forex_error:
                    error_exchange = "FX"
                elif is_index_error:
                    error_exchange = "INDEX"
                else:
                    error_exchange = "Unknown"
                
                results[symbol] = {
                    "symbol": symbol,
                    "name": symbol,
                    "currency": error_currency,
                    "exchange": error_exchange,
                    "current_price": 0,
                    "previous_close": 0,
                    "price_change": 0,
                    "price_change_percent": 0,
                    "volume": 0 if is_forex_error else 0,
                    "market_cap": 0 if (is_forex_error or is_index_error) else 0,
                    "pe_ratio": 0 if (is_forex_error or is_index_error) else 0,
                    "dividend_yield": 0 if (is_forex_error or is_index_error) else 0,
                    "fifty_two_week_high": 0,
                    "fifty_two_week_low": 0,
                    "timestamp": time.time(),
                }

        return results

    def _is_cached(self, symbol: str) -> bool:
        """キャッシュが有効かチェックする.

        Args:
            symbol: チェックする銘柄シンボル

        Returns:
            キャッシュが有効ならTrue、そうでなければFalse
        """
        return self.cache.get(symbol) is not None

    def get_cache_stats(self) -> dict[str, Any]:
        """キャッシュの統計情報を取得する.
        
        Returns:
            キャッシュ統計情報
        """
        return self.cache.get_stats()

    def cleanup_cache(self) -> int:
        """期限切れのキャッシュをクリーンアップする.
        
        Returns:
            削除されたアイテム数
        """
        return self.cache.cleanup_expired()
