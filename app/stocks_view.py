from flask import request, jsonify
from datetime import datetime
from base_view import BaseView


class StocksView(BaseView):
    def get(self):
        # 配列パラメータ対応
        symbols_list = request.args.getlist("symbols")

        if not symbols_list:
            # 単一パラメータの場合（カンマ区切り）
            symbols_param = request.args.get("symbols", "AAPL,GOOGL")
            symbols = [s.strip().upper() for s in symbols_param.split(",") if s.strip()]
        else:
            # 配列パラメータの場合
            symbols = [s.strip().upper() for s in symbols_list if s.strip()]

        stock_data = self.app.fetcher.get_stock_data(symbols)

        return jsonify(
            {
                "timestamp": datetime.now().isoformat(),
                "symbols": symbols,
                "data": stock_data,
            }
        )
