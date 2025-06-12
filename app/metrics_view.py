"""メトリクスビューモジュール."""

import logging
from typing import Any

from prometheus_client import generate_latest

from base_view import BaseView

logger = logging.getLogger(__name__)


class MetricsView(BaseView):
    """メトリクス収集用ビュークラス."""

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

    def _is_crypto(self, symbol: str) -> bool:
        """シンボルが暗号通貨かどうかを判定する.
        
        Args:
            symbol: 判定するシンボル
            
        Returns:
            暗号通貨ならTrue、そうでなければFalse
        """
        # 主要な暗号通貨シンボル
        known_cryptocurrencies = [
            "BTC-USD", "ETH-USD", "ADA-USD", "XRP-USD", "SOL-USD",
            "DOGE-USD", "DOT-USD", "MATIC-USD", "LTC-USD", "BCH-USD",
            "LINK-USD", "XLM-USD", "ALGO-USD", "ATOM-USD", "AVAX-USD"
        ]
        return symbol in known_cryptocurrencies

    def _create_metric_labels(self, data: dict[str, Any]) -> dict[str, str]:
        """メトリクス用の基本ラベルを作成する.
        
        Args:
            data: 株価データ
            
        Returns:
            メトリクス用ラベル辞書
        """
        return {
            "symbol": data["symbol"],
            "name": data["name"],
            "exchange": data["exchange"],
        }

    def _create_price_labels(self, data: dict[str, Any]) -> dict[str, str]:
        """価格メトリクス用の拡張ラベルを作成する.
        
        Args:
            data: 株価データ
            
        Returns:
            価格メトリクス用ラベル辞書
        """
        return {
            "symbol": data["symbol"],
            "name": data["name"],
            "currency": data["currency"],
            "exchange": data["exchange"],
        }

    def _update_price_metrics(self, data: dict[str, Any], metrics_factory: Any) -> None:
        """価格関連メトリクスを更新する.
        
        Args:
            data: 株価データ、為替レートデータ、指数データ、または暗号通貨データ
            metrics_factory: メトリクスファクトリー
        """
        price_labels = self._create_price_labels(data)
        is_forex = self._is_forex_pair(data["symbol"])
        is_index = self._is_index(data["symbol"])
        is_crypto = self._is_crypto(data["symbol"])

        if is_forex:
            metric_key = "forex_rate"
        elif is_index:
            metric_key = "index_value"
        elif is_crypto:
            metric_key = "crypto_price"
        else:
            metric_key = "stock_price"
            
        metrics_factory.get_metric(metric_key).labels(**price_labels).set(
            data["current_price"]
        )

    def _update_volume_and_market_metrics(self, data: dict[str, Any], metrics_factory: Any) -> None:
        """出来高・市場関連メトリクスを更新する.
        
        Args:
            data: 株価データ、指数データ、または暗号通貨データ
            metrics_factory: メトリクスファクトリー
        """
        is_forex = self._is_forex_pair(data["symbol"])
        is_index = self._is_index(data["symbol"])
        is_crypto = self._is_crypto(data["symbol"])
        
        # 為替ペアの場合は何も更新しない
        if is_forex:
            return

        labels = self._create_metric_labels(data)

        # 出来高メトリクスの更新
        if is_index:
            # 指数の場合
            metrics_factory.get_metric("index_volume").labels(**labels).set(
                data["volume"]
            )
        elif is_crypto:
            # 暗号通貨の場合
            metrics_factory.get_metric("crypto_volume").labels(**labels).set(
                data["volume"]
            )
            # 暗号通貨の時価総額
            metrics_factory.get_metric("crypto_market_cap").labels(**labels).set(
                data["market_cap"]
            )
        else:
            # 株式の場合
            metrics_factory.get_metric("stock_volume").labels(**labels).set(
                data["volume"]
            )
            # 株式固有のメトリクス
            metrics_factory.get_metric("stock_market_cap").labels(**labels).set(
                data["market_cap"]
            )
            metrics_factory.get_metric("stock_pe_ratio").labels(**labels).set(
                data["pe_ratio"]
            )

            # 配当利回りは%表示のため100倍
            dividend_yield = data["dividend_yield"] * 100 if data["dividend_yield"] else 0
            metrics_factory.get_metric("stock_dividend_yield").labels(**labels).set(
                dividend_yield
            )

    def _update_range_metrics(self, data: dict[str, Any], metrics_factory: Any) -> None:
        """52週レンジ関連メトリクスを更新する.
        
        Args:
            data: 株価データ、為替レートデータ、指数データ、または暗号通貨データ
            metrics_factory: メトリクスファクトリー
        """
        labels = self._create_metric_labels(data)
        is_forex = self._is_forex_pair(data["symbol"])
        is_index = self._is_index(data["symbol"])
        is_crypto = self._is_crypto(data["symbol"])

        if is_forex:
            high_key = "forex_52week_high"
            low_key = "forex_52week_low"
        elif is_index:
            high_key = "index_52week_high"
            low_key = "index_52week_low"
        elif is_crypto:
            high_key = "crypto_52week_high"
            low_key = "crypto_52week_low"
        else:
            high_key = "stock_52week_high"
            low_key = "stock_52week_low"

        metrics_factory.get_metric(high_key).labels(**labels).set(
            data["fifty_two_week_high"]
        )
        metrics_factory.get_metric(low_key).labels(**labels).set(
            data["fifty_two_week_low"]
        )

    def _update_change_metrics(self, data: dict[str, Any], metrics_factory: Any) -> None:
        """価格変動関連メトリクスを更新する.
        
        Args:
            data: 株価データ、為替レートデータ、指数データ、または暗号通貨データ
            metrics_factory: メトリクスファクトリー
        """
        labels = self._create_metric_labels(data)
        is_forex = self._is_forex_pair(data["symbol"])
        is_index = self._is_index(data["symbol"])
        is_crypto = self._is_crypto(data["symbol"])

        if is_forex:
            close_key = "forex_previous_close"
            change_key = "forex_rate_change"
            change_percent_key = "forex_rate_change_percent"
        elif is_index:
            close_key = "index_previous_close"
            change_key = "index_value_change"
            change_percent_key = "index_value_change_percent"
        elif is_crypto:
            close_key = "crypto_previous_close"
            change_key = "crypto_price_change"
            change_percent_key = "crypto_price_change_percent"
        else:
            close_key = "stock_previous_close"
            change_key = "stock_price_change"
            change_percent_key = "stock_price_change_percent"

        metrics_factory.get_metric(close_key).labels(**labels).set(
            data["previous_close"]
        )
        metrics_factory.get_metric(change_key).labels(**labels).set(
            data["price_change"]
        )
        metrics_factory.get_metric(change_percent_key).labels(**labels).set(
            data["price_change_percent"]
        )

    def _update_timestamp_metrics(self, data: dict[str, Any], metrics_factory: Any) -> None:
        """タイムスタンプ関連メトリクスを更新する.
        
        Args:
            data: 株価データ、為替レートデータ、指数データ、または暗号通貨データ
            metrics_factory: メトリクスファクトリー
        """
        is_forex = self._is_forex_pair(data["symbol"])
        is_index = self._is_index(data["symbol"])
        is_crypto = self._is_crypto(data["symbol"])
        
        if is_forex:
            timestamp_key = "forex_last_updated"
        elif is_index:
            timestamp_key = "index_last_updated"
        elif is_crypto:
            timestamp_key = "crypto_last_updated"
        else:
            timestamp_key = "stock_last_updated"

        metrics_factory.get_metric(timestamp_key).labels(
            symbol=data["symbol"]
        ).set(data["timestamp"])

    def update_prometheus_metrics(self, stock_data_dict: dict[str, Any]) -> None:
        """PrometheusメトリクスをStock data、Forex data、Index data、またはCrypto dataで更新する.

        Args:
            stock_data_dict: 銘柄別の株価データ、為替レートデータ、指数データ、または暗号通貨データ辞書
        """
        # MetricsFactoryをインポート（循環インポート回避）
        from main import metrics_factory

        for symbol, data in stock_data_dict.items():
            try:
                # 各カテゴリのメトリクスを更新
                self._update_price_metrics(data, metrics_factory)
                self._update_volume_and_market_metrics(data, metrics_factory)
                self._update_range_metrics(data, metrics_factory)
                self._update_change_metrics(data, metrics_factory)
                self._update_timestamp_metrics(data, metrics_factory)

            except Exception as e:
                logger.error(f"Error updating metrics for {symbol}: {e}")
                is_forex = self._is_forex_pair(symbol)
                is_index = self._is_index(symbol)
                is_crypto = self._is_crypto(symbol)
                
                if is_forex:
                    error_key = "forex_fetch_errors"
                elif is_index:
                    error_key = "index_fetch_errors"
                elif is_crypto:
                    error_key = "crypto_fetch_errors"
                else:
                    error_key = "stock_fetch_errors"
                    
                metrics_factory.get_metric(error_key).labels(
                    symbol=symbol, error_type="metric_update_error"
                ).inc()

    def get(self) -> tuple[str, int, dict[str, str]]:
        """メトリクスデータを収集してPrometheus形式で返す.

        Returns:
            Prometheusメトリクスデータ、ステータスコード、ヘッダーのタプル
        """
        try:
            # URLパラメータから銘柄リストを取得
            symbols = self._parse_symbols_parameter()

            logger.info(f"Fetching metrics for symbols: {symbols}")

            # 株価データまたは為替レートデータ取得
            stock_data = self.app.fetcher.get_stock_data(symbols)

            # メトリクス更新
            self.update_prometheus_metrics(stock_data)

            return generate_latest(), 200, {"Content-Type": "text/plain; charset=utf-8"}

        except ValueError as e:
            logger.warning(f"Invalid input parameters: {e}")
            return generate_latest(), 400, {"Content-Type": "text/plain; charset=utf-8"}
        except Exception as e:
            logger.error(f"Error in metrics endpoint: {e}")
            return generate_latest(), 500, {"Content-Type": "text/plain; charset=utf-8"}
