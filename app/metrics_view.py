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
            data: 株価データまたは為替レートデータ
            metrics_factory: メトリクスファクトリー
        """
        price_labels = self._create_price_labels(data)
        is_forex = self._is_forex_pair(data["symbol"])

        metric_key = "forex_rate" if is_forex else "stock_price"
        metrics_factory.get_metric(metric_key).labels(**price_labels).set(
            data["current_price"]
        )

    def _update_volume_and_market_metrics(self, data: dict[str, Any], metrics_factory: Any) -> None:
        """出来高・市場関連メトリクスを更新する（株式のみ）.
        
        Args:
            data: 株価データ
            metrics_factory: メトリクスファクトリー
        """
        # 為替ペアの場合は出来高・市場関連メトリクスを更新しない
        if self._is_forex_pair(data["symbol"]):
            return

        labels = self._create_metric_labels(data)

        metrics_factory.get_metric("stock_volume").labels(**labels).set(
            data["volume"]
        )
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
            data: 株価データまたは為替レートデータ
            metrics_factory: メトリクスファクトリー
        """
        labels = self._create_metric_labels(data)
        is_forex = self._is_forex_pair(data["symbol"])

        high_key = "forex_52week_high" if is_forex else "stock_52week_high"
        low_key = "forex_52week_low" if is_forex else "stock_52week_low"

        metrics_factory.get_metric(high_key).labels(**labels).set(
            data["fifty_two_week_high"]
        )
        metrics_factory.get_metric(low_key).labels(**labels).set(
            data["fifty_two_week_low"]
        )

    def _update_change_metrics(self, data: dict[str, Any], metrics_factory: Any) -> None:
        """価格変動関連メトリクスを更新する.
        
        Args:
            data: 株価データまたは為替レートデータ
            metrics_factory: メトリクスファクトリー
        """
        labels = self._create_metric_labels(data)
        is_forex = self._is_forex_pair(data["symbol"])

        close_key = "forex_previous_close" if is_forex else "stock_previous_close"
        change_key = "forex_rate_change" if is_forex else "stock_price_change"
        change_percent_key = "forex_rate_change_percent" if is_forex else "stock_price_change_percent"

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
            data: 株価データまたは為替レートデータ
            metrics_factory: メトリクスファクトリー
        """
        is_forex = self._is_forex_pair(data["symbol"])
        timestamp_key = "forex_last_updated" if is_forex else "stock_last_updated"

        metrics_factory.get_metric(timestamp_key).labels(
            symbol=data["symbol"]
        ).set(data["timestamp"])

    def update_prometheus_metrics(self, stock_data_dict: dict[str, Any]) -> None:
        """PrometheusメトリクスをStock dataまたはForex dataで更新する.

        Args:
            stock_data_dict: 銘柄別の株価データまたは為替レートデータ辞書
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
                error_key = "forex_fetch_errors" if is_forex else "stock_fetch_errors"
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
