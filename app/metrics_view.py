"""メトリクスビューモジュール."""

import logging
from typing import Any

from flask import request
from prometheus_client import generate_latest

from base_view import BaseView

logger = logging.getLogger(__name__)


class MetricsView(BaseView):
    """メトリクス収集用ビュークラス."""

    def update_prometheus_metrics(self, stock_data_dict: dict[str, Any]) -> None:
        """PrometheusメトリクスをStock dataで更新する.

        Args:
            stock_data_dict: 銘柄別の株価データ辞書
        """
        # MetricsFactoryをインポート（循環インポート回避）
        from main import metrics_factory

        for symbol, data in stock_data_dict.items():
            try:
                labels = {
                    "symbol": data["symbol"],
                    "name": data["name"],
                    "exchange": data["exchange"],
                }

                # 価格関連メトリクス
                metrics_factory.get_metric("stock_price").labels(
                    symbol=data["symbol"],
                    name=data["name"],
                    currency=data["currency"],
                    exchange=data["exchange"],
                ).set(data["current_price"])

                metrics_factory.get_metric("stock_volume").labels(**labels).set(
                    data["volume"]
                )
                metrics_factory.get_metric("stock_market_cap").labels(**labels).set(
                    data["market_cap"]
                )
                metrics_factory.get_metric("stock_pe_ratio").labels(**labels).set(
                    data["pe_ratio"]
                )
                metrics_factory.get_metric("stock_dividend_yield").labels(**labels).set(
                    data["dividend_yield"] * 100 if data["dividend_yield"] else 0
                )
                metrics_factory.get_metric("stock_52week_high").labels(**labels).set(
                    data["fifty_two_week_high"]
                )
                metrics_factory.get_metric("stock_52week_low").labels(**labels).set(
                    data["fifty_two_week_low"]
                )

                # 前日比関連メトリクス
                metrics_factory.get_metric("stock_previous_close").labels(**labels).set(
                    data["previous_close"]
                )
                metrics_factory.get_metric("stock_price_change").labels(**labels).set(
                    data["price_change"]
                )
                metrics_factory.get_metric("stock_price_change_percent").labels(
                    **labels
                ).set(data["price_change_percent"])

                # 最終更新時刻
                metrics_factory.get_metric("stock_last_updated").labels(
                    symbol=data["symbol"]
                ).set(data["timestamp"])

            except Exception as e:
                logger.error(f"Error updating metrics for {symbol}: {e}")
                metrics_factory.get_metric("stock_fetch_errors").labels(
                    symbol=symbol, error_type="metric_update_error"
                ).inc()

    def _parse_symbols_parameter(self) -> list[str]:
        """URLパラメータからsymbolsを解析して銘柄リストを返す.

        以下の形式をサポート:
        - ?symbols=AAPL,GOOGL (カンマ区切り文字列)
        - ?symbols=AAPL&symbols=GOOGL (配列形式)
        - ?symbols=AAPL,GOOGL&symbols=MSFT (混合形式)

        Returns:
            正規化された銘柄リスト
        """
        # URLパラメータから全ての symbols 値を取得
        symbols_list = request.args.getlist("symbols")

        # symbols パラメータが全く存在しない場合
        if "symbols" not in request.args:
            return ["AAPL", "GOOGL", "MSFT", "TSLA"]

        # 全てのパラメータ値を処理
        symbols = []
        for param_value in symbols_list:
            if param_value:
                # カンマ区切りの可能性を考慮して分割
                split_symbols = [s.strip().upper() for s in param_value.split(",") if s.strip()]
                symbols.extend(split_symbols)

        # 重複を除去しつつ順序を保持
        unique_symbols = []
        seen = set()
        for symbol in symbols:
            if symbol not in seen:
                unique_symbols.append(symbol)
                seen.add(symbol)

        return unique_symbols if unique_symbols else ["AAPL", "GOOGL", "MSFT", "TSLA"]

    def get(self) -> tuple[str, int, dict[str, str]]:
        """メトリクスデータを収集してPrometheus形式で返す.

        Returns:
            Prometheusメトリクスデータ、ステータスコード、ヘッダーのタプル
        """
        try:
            # URLパラメータから銘柄リストを取得
            symbols = self._parse_symbols_parameter()


            logger.info(f"Fetching metrics for symbols: {symbols}")

            # 株価データ取得
            stock_data = self.app.fetcher.get_stock_data(symbols)

            # メトリクス更新
            self.update_prometheus_metrics(stock_data)

            return generate_latest(), 200, {"Content-Type": "text/plain; charset=utf-8"}

        except Exception as e:
            logger.error(f"Error in metrics endpoint: {e}")
            return generate_latest(), 500, {"Content-Type": "text/plain; charset=utf-8"}
