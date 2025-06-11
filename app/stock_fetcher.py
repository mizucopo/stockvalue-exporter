"""株価データフェッチャーモジュール."""

import logging
import time
from typing import Any

import yfinance as yf
from prometheus_client import Counter, Histogram

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
        self.cache = {}
        self.cache_ttl = 600  # 10分間キャッシュ
        self.stock_fetch_duration = stock_fetch_duration
        self.stock_fetch_errors = stock_fetch_errors

    def get_stock_data(self, symbols: list[str]) -> dict[str, Any]:
        """指定された銘柄の株価データを取得する.

        Args:
            symbols: 取得する銘柄シンボルのリスト

        Returns:
            銘柄別の株価データ辞書
        """
        results = {}

        for symbol in symbols:
            start_time = time.time()

            try:
                # キャッシュチェック
                if self._is_cached(symbol):
                    results[symbol] = self.cache[symbol]["data"]
                    continue

                # Yahoo Finance APIから株価データ取得
                ticker = yf.Ticker(symbol)
                info = ticker.info

                if not info:
                    raise ValueError(f"No data found for symbol: {symbol}")

                # 株価データの構造化
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

                stock_data = {
                    "symbol": symbol,
                    "name": info.get("longName", info.get("shortName", symbol)),
                    "currency": info.get("currency", "USD"),
                    "exchange": info.get("exchange", "Unknown"),
                    "current_price": current_price,
                    "previous_close": previous_close,
                    "price_change": price_change,
                    "price_change_percent": price_change_percent,
                    "volume": info.get("volume", info.get("regularMarketVolume", 0)),
                    "market_cap": info.get("marketCap", 0),
                    "pe_ratio": info.get("trailingPE", 0),
                    "dividend_yield": info.get("dividendYield", 0),
                    "fifty_two_week_high": info.get("fiftyTwoWeekHigh", 0),
                    "fifty_two_week_low": info.get("fiftyTwoWeekLow", 0),
                    "timestamp": time.time(),
                }

                # キャッシュに保存
                self.cache[symbol] = {"data": stock_data, "timestamp": time.time()}

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

                # エラー時のデフォルト値
                results[symbol] = {
                    "symbol": symbol,
                    "name": symbol,
                    "currency": "USD",
                    "exchange": "Unknown",
                    "current_price": 0,
                    "previous_close": 0,
                    "price_change": 0,
                    "price_change_percent": 0,
                    "volume": 0,
                    "market_cap": 0,
                    "pe_ratio": 0,
                    "dividend_yield": 0,
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
        if symbol not in self.cache:
            return False

        cache_age = time.time() - self.cache[symbol]["timestamp"]
        return cache_age < self.cache_ttl
