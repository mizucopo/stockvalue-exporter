"""メトリクスビューモジュール."""

import logging
from typing import Any, Protocol

from prometheus_client import Counter, Gauge, Histogram, generate_latest

from base_view import BaseView
from symbol_classifier import SymbolClassifier


class MetricsFactoryProtocol(Protocol):
    """メトリクスファクトリーのプロトコル."""

    def get_metric(self, metric_key: str) -> Gauge | Counter | Histogram | None:
        """指定されたキーのメトリクスを取得する."""
        ...

    def clear_all_metrics(self) -> None:
        """全てのメトリクスをクリアする."""
        ...


logger = logging.getLogger(__name__)


class MetricsView(BaseView):
    """メトリクス収集用ビュークラス."""

    def _set_gauge_metric(
        self,
        metric: Gauge | Counter | Histogram | None,
        labels: dict[str, str],
        value: float,
    ) -> None:
        """Gaugeメトリクスに値を設定する（型安全）."""
        if metric is not None and isinstance(metric, Gauge):
            metric.labels(**labels).set(value)

    def _increment_counter_metric(
        self, metric: Gauge | Counter | Histogram | None, labels: dict[str, str]
    ) -> None:
        """Counterメトリクスをインクリメントする（型安全）."""
        if metric is not None and isinstance(metric, Counter):
            metric.labels(**labels).inc()

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
            "asset_type": data["asset_type"],
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
            "asset_type": data["asset_type"],
        }

    def _update_price_metrics(
        self, data: dict[str, Any], metrics_factory: MetricsFactoryProtocol
    ) -> None:
        """価格関連メトリクスを更新する.

        Args:
            data: 株価データ、為替レートデータ、指数データ、または暗号通貨データ
            metrics_factory: メトリクスファクトリー
        """
        price_labels = self._create_price_labels(data)

        # 統一メトリクス: financial_price
        metric = metrics_factory.get_metric("financial_price")
        self._set_gauge_metric(metric, price_labels, data["current_price"])

    def _update_volume_and_market_metrics(
        self, data: dict[str, Any], metrics_factory: MetricsFactoryProtocol
    ) -> None:
        """出来高・市場関連メトリクスを更新する.

        Args:
            data: 株価データ、指数データ、または暗号通貨データ
            metrics_factory: メトリクスファクトリー
        """
        asset_type = data["asset_type"]
        labels = self._create_metric_labels(data)

        # 出来高メトリクスの更新（為替以外）
        if asset_type != "forex":
            volume_metric = metrics_factory.get_metric("financial_volume")
            self._set_gauge_metric(volume_metric, labels, data["volume"])

        # 時価総額メトリクスの更新（株式・暗号通貨のみ）
        if asset_type in ["stock", "crypto"]:
            market_cap_metric = metrics_factory.get_metric("financial_market_cap")
            self._set_gauge_metric(market_cap_metric, labels, data["market_cap"])

        # 株式特有メトリクスの更新
        if asset_type == "stock":
            # PER
            pe_metric = metrics_factory.get_metric("financial_pe_ratio")
            self._set_gauge_metric(pe_metric, labels, data["pe_ratio"])

            # 配当利回り（%表示のため100倍）
            dividend_value = data["dividend_yield"] * 100 if data["dividend_yield"] else 0
            dividend_metric = metrics_factory.get_metric("financial_dividend_yield")
            self._set_gauge_metric(dividend_metric, labels, dividend_value)

    def _update_range_metrics(
        self, data: dict[str, Any], metrics_factory: MetricsFactoryProtocol
    ) -> None:
        """52週レンジ関連メトリクスを更新する.

        Args:
            data: 株価データ、為替レートデータ、指数データ、または暗号通貨データ
            metrics_factory: メトリクスファクトリー
        """
        labels = self._create_metric_labels(data)

        # 統一メトリクス: financial_52week_high/low
        high_metric = metrics_factory.get_metric("financial_52week_high")
        low_metric = metrics_factory.get_metric("financial_52week_low")

        self._set_gauge_metric(high_metric, labels, data["fifty_two_week_high"])
        self._set_gauge_metric(low_metric, labels, data["fifty_two_week_low"])

    def _update_change_metrics(
        self, data: dict[str, Any], metrics_factory: MetricsFactoryProtocol
    ) -> None:
        """価格変動関連メトリクスを更新する.

        Args:
            data: 株価データ、為替レートデータ、指数データ、または暗号通貨データ
            metrics_factory: メトリクスファクトリー
        """
        labels = self._create_metric_labels(data)

        # 統一メトリクス: financial_previous_close, financial_price_change, financial_price_change_percent
        close_metric = metrics_factory.get_metric("financial_previous_close")
        change_metric = metrics_factory.get_metric("financial_price_change")
        change_percent_metric = metrics_factory.get_metric("financial_price_change_percent")

        self._set_gauge_metric(close_metric, labels, data["previous_close"])
        self._set_gauge_metric(change_metric, labels, data["price_change"])
        self._set_gauge_metric(
            change_percent_metric, labels, data["price_change_percent"]
        )

    def _update_timestamp_metrics(
        self, data: dict[str, Any], metrics_factory: MetricsFactoryProtocol
    ) -> None:
        """タイムスタンプ関連メトリクスを更新する.

        Args:
            data: 株価データ、為替レートデータ、指数データ、または暗号通貨データ
            metrics_factory: メトリクスファクトリー
        """
        # 統一メトリクス: financial_last_updated
        timestamp_metric = metrics_factory.get_metric("financial_last_updated")
        timestamp_labels = {"symbol": data["symbol"], "asset_type": data["asset_type"]}
        self._set_gauge_metric(timestamp_metric, timestamp_labels, data["timestamp"])

    def update_prometheus_metrics(self, stock_data_dict: dict[str, Any]) -> None:
        """PrometheusメトリクスをStock data、Forex data、Index data、またはCrypto dataで更新する.

        Args:
            stock_data_dict: 銘柄別の株価データ、為替レートデータ、指数データ、または暗号通貨データ辞書
        """
        metrics_factory = self.app.metrics_factory

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
                asset_type = data.get("asset_type", SymbolClassifier.get_asset_type(symbol).value)

                # 統一メトリクス: financial_fetch_errors
                error_metric = metrics_factory.get_metric("financial_fetch_errors")
                error_labels = {"symbol": symbol, "error_type": "metric_update_error", "asset_type": asset_type}
                self._increment_counter_metric(error_metric, error_labels)

    def get(self) -> tuple[str, int, dict[str, str]]:
        """メトリクスデータを収集してPrometheus形式で返す.

        Returns:
            Prometheusメトリクスデータ、ステータスコード、ヘッダーのタプル
        """
        try:
            # リクエストパラメータの解析
            symbols, clear_metrics = self._parse_request_parameters()

            # ログ出力
            self._log_request_info(symbols, clear_metrics)

            # メトリクスクリア処理
            if clear_metrics:
                self._clear_existing_metrics()

            # データ取得とメトリクス更新
            stock_data = self.app.fetcher.get_stock_data(symbols)
            self.update_prometheus_metrics(stock_data)

            return self._create_success_response()

        except ValueError as e:
            return self._handle_validation_error(e)
        except Exception as e:
            return self._handle_general_error(e)

    def _get_clear_flags(self) -> tuple[bool, bool, bool, bool]:
        """メトリクスクリア関連のフラグを取得する.

        Returns:
            url_clear, only_requested, auto_clear, clear_metricsのタプル
        """
        from flask import request

        from config import config

        url_clear = request.args.get("clear", "false").lower() in ["true", "1", "yes"]
        only_requested = request.args.get("only_requested", "false").lower() in [
            "true",
            "1",
            "yes",
        ]
        auto_clear = config.AUTO_CLEAR_METRICS
        clear_metrics = url_clear or auto_clear or only_requested

        return url_clear, only_requested, auto_clear, clear_metrics

    def _parse_request_parameters(self) -> tuple[list[str], bool]:
        """リクエストパラメータを解析する.

        Returns:
            シンボルリストとメトリクスクリアフラグのタプル
        """
        # URLパラメータから銘柄リストを取得
        symbols = self._parse_symbols_parameter()

        # メトリクスクリアオプションを確認
        _, _, _, clear_metrics = self._get_clear_flags()

        return symbols, clear_metrics

    def _log_request_info(self, symbols: list[str], clear_metrics: bool) -> None:
        """リクエスト情報をログ出力する.

        Args:
            symbols: 銘柄リスト
            clear_metrics: メトリクスクリアフラグ
        """
        url_clear, only_requested, auto_clear, _ = self._get_clear_flags()

        logger.info(
            f"Fetching metrics for symbols: {symbols}, clear_metrics: {clear_metrics} "
            f"(url: {url_clear}, auto: {auto_clear}, only_requested: {only_requested})"
        )

    def _clear_existing_metrics(self) -> None:
        """既存のメトリクスをクリアする."""
        self.app.metrics_factory.clear_all_metrics()
        logger.info("Cleared all existing metrics before fetching new data")

    def _create_success_response(self) -> tuple[str, int, dict[str, str]]:
        """成功レスポンスを作成する.

        Returns:
            Prometheusメトリクスデータ、ステータスコード、ヘッダーのタプル
        """
        return (
            generate_latest().decode("utf-8"),
            200,
            {"Content-Type": "text/plain; charset=utf-8"},
        )

    def _handle_validation_error(
        self, error: ValueError
    ) -> tuple[str, int, dict[str, str]]:
        """バリデーションエラーを処理する.

        Args:
            error: 発生したバリデーションエラー

        Returns:
            エラーレスポンスのタプル
        """
        logger.warning(f"Invalid input parameters: {error}")
        return (
            generate_latest().decode("utf-8"),
            400,
            {"Content-Type": "text/plain; charset=utf-8"},
        )

    def _handle_general_error(
        self, error: Exception
    ) -> tuple[str, int, dict[str, str]]:
        """一般的なエラーを処理する.

        Args:
            error: 発生したエラー

        Returns:
            エラーレスポンスのタプル
        """
        logger.error(f"Error in metrics endpoint: {error}")
        return (
            generate_latest().decode("utf-8"),
            500,
            {"Content-Type": "text/plain; charset=utf-8"},
        )
