"""株価データフェッチャーモジュール."""

import logging
import time
from typing import Any

import yfinance as yf  # type: ignore[import-untyped]
from prometheus_client import Counter, Histogram

from cache import LRUCache
from symbol_classifier import AssetType, SymbolClassifier

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
        self.cache: LRUCache[dict[str, Any]] = LRUCache()
        self.cache_ttl = self.cache.ttl_seconds  # テスト用のプロパティ
        self.stock_fetch_duration = stock_fetch_duration
        self.stock_fetch_errors = stock_fetch_errors

    def _calculate_price_changes(
        self, current_price: float, previous_close: float
    ) -> tuple[float, float]:
        """価格変動を計算する.

        Args:
            current_price: 現在価格
            previous_close: 前日終値

        Returns:
            価格変動額と価格変動率のタプル
        """
        price_change = current_price - previous_close if previous_close else 0
        price_change_percent = (
            (price_change / previous_close * 100) if previous_close else 0
        )
        return price_change, price_change_percent

    def _create_stock_data(
        self, symbol: str, info: dict[str, Any], asset_type: AssetType
    ) -> dict[str, Any]:
        """株価データ構造を作成する.

        Args:
            symbol: 銘柄シンボル
            info: Yahoo Finance APIから取得した情報
            asset_type: 資産タイプ

        Returns:
            統一された株価データ構造
        """
        # 価格情報の取得
        current_price = info.get("currentPrice", info.get("regularMarketPrice", 0))
        previous_close = info.get(
            "previousClose", info.get("regularMarketPreviousClose", 0)
        )

        # 価格変動の計算
        price_change, price_change_percent = self._calculate_price_changes(
            current_price, previous_close
        )

        # 資産タイプ別の条件設定
        is_forex = asset_type == AssetType.FOREX
        is_index = asset_type == AssetType.INDEX
        is_crypto = asset_type == AssetType.CRYPTO

        # 通貨と取引所の設定
        currency = SymbolClassifier.get_currency_for_symbol(symbol)
        exchange = SymbolClassifier.get_exchange_for_symbol(symbol)

        # 株式の場合は、API情報がある場合はそれを使用
        if asset_type == AssetType.STOCK:
            api_currency = info.get("currency")
            api_exchange = info.get("exchange")
            if api_currency:
                currency = api_currency
            if api_exchange:
                exchange = api_exchange
        elif not is_forex and not is_index and not is_crypto:
            # 株式以外でAPI情報がある場合
            api_currency = info.get("currency")
            if api_currency:
                currency = api_currency

        return {
            "symbol": symbol,
            "name": info.get("longName", info.get("shortName", symbol)),
            "currency": currency,
            "exchange": exchange,
            "current_price": current_price,
            "previous_close": previous_close,
            "price_change": price_change,
            "price_change_percent": price_change_percent,
            "volume": (
                0
                if is_forex
                else info.get("volume", info.get("regularMarketVolume", 0))
            ),
            "market_cap": 0 if (is_forex or is_index) else info.get("marketCap", 0),
            "pe_ratio": (
                0 if (is_forex or is_index or is_crypto) else info.get("trailingPE", 0)
            ),
            "dividend_yield": (
                0
                if (is_forex or is_index or is_crypto)
                else info.get("dividendYield", 0)
            ),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh", 0),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow", 0),
            "timestamp": time.time(),
        }

    def _create_error_data(self, symbol: str) -> dict[str, Any]:
        """エラー時のデフォルトデータを作成する.

        Args:
            symbol: 銘柄シンボル

        Returns:
            エラー時のデフォルト株価データ構造
        """
        error_asset_type = SymbolClassifier.get_asset_type(symbol)
        is_forex_error = error_asset_type == AssetType.FOREX
        is_index_error = error_asset_type == AssetType.INDEX
        is_crypto_error = error_asset_type == AssetType.CRYPTO

        error_currency = SymbolClassifier.get_currency_for_symbol(symbol)
        error_exchange = SymbolClassifier.get_exchange_for_symbol(symbol)

        return {
            "symbol": symbol,
            "name": symbol,
            "currency": error_currency,
            "exchange": error_exchange,
            "current_price": 0,
            "previous_close": 0,
            "price_change": 0,
            "price_change_percent": 0,
            "volume": 0,
            "market_cap": 0 if (is_forex_error or is_index_error) else 0,
            "pe_ratio": (
                0 if (is_forex_error or is_index_error or is_crypto_error) else 0
            ),
            "dividend_yield": (
                0 if (is_forex_error or is_index_error or is_crypto_error) else 0
            ),
            "fifty_two_week_high": 0,
            "fifty_two_week_low": 0,
            "timestamp": time.time(),
        }

    def _record_metrics(
        self,
        symbol: str,
        start_time: float,
        success: bool = True,
        error: Exception | None = None,
    ) -> None:
        """メトリクスを記録する.

        Args:
            symbol: 銘柄シンボル
            start_time: 開始時刻
            success: 成功フラグ
            error: エラー（失敗時）
        """
        if success and self.stock_fetch_duration:
            duration = time.time() - start_time
            self.stock_fetch_duration.labels(symbol=symbol).observe(duration)
        elif not success and self.stock_fetch_errors and error:
            self.stock_fetch_errors.labels(
                symbol=symbol, error_type=type(error).__name__
            ).inc()

    def get_stock_data(self, symbols: list[str]) -> dict[str, Any]:
        """指定された銘柄の株価データ、為替レートデータ、指数データ、または暗号通貨データを取得する.

        Args:
            symbols: 取得する銘柄シンボル、為替ペア、指数、または暗号通貨のリスト

        Returns:
            銘柄別の株価データ、為替レートデータ、指数データ、または暗号通貨データ辞書
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

                # 資産タイプの判定
                asset_type = SymbolClassifier.get_asset_type(symbol)

                # 株価データ構造を作成
                stock_data = self._create_stock_data(symbol, info, asset_type)

                # キャッシュに保存
                self.cache.put(symbol, stock_data)
                results[symbol] = stock_data

                # 成功メトリクス記録
                self._record_metrics(symbol, start_time, success=True)

                logger.info(
                    f"Successfully fetched data for {symbol}: ${stock_data['current_price']} "
                    f"(${stock_data['price_change']:+.2f}, {stock_data['price_change_percent']:+.2f}%)"
                )

            except Exception as e:
                logger.error(f"Error fetching data for {symbol}: {e}")

                # エラーメトリクス記録
                self._record_metrics(symbol, start_time, success=False, error=e)

                # エラー時のデフォルトデータを作成
                results[symbol] = self._create_error_data(symbol)

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
