"""株価データビューモジュール."""

import logging
from datetime import datetime

from flask import Response, jsonify

from base_view import BaseView

logger = logging.getLogger(__name__)


class StocksView(BaseView):
    """株価データ取得用ビュークラス."""

    def get(self) -> Response:
        """指定された銘柄の株価データを取得して返す.

        URLパラメータからsymbolsを取得し、株価データをフェッチして返す.

        Returns:
            株価データを含むJSONレスポンス
        """
        try:
            # URLパラメータから銘柄リストを取得
            symbols = self._parse_symbols_parameter()

            logger.info(f"Fetching stock data for symbols: {symbols}")

            stock_data = self.app.fetcher.get_stock_data(symbols)

            return jsonify(
                {
                    "timestamp": datetime.now().isoformat(),
                    "symbols": symbols,
                    "data": stock_data,
                }
            )

        except ValueError as e:
            logger.warning(f"Invalid input parameters: {e}")
            response = jsonify(
                {
                    "error": "Invalid input parameters",
                    "message": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            )
            response.status_code = 400
            return response

        except Exception as e:
            logger.error(f"Error in stocks endpoint: {e}")
            response = jsonify(
                {
                    "error": "Internal server error",
                    "message": "An error occurred while fetching stock data",
                    "timestamp": datetime.now().isoformat(),
                }
            )
            response.status_code = 500
            return response
