"""株価データビューモジュール."""

from datetime import datetime

from flask import Response, jsonify, request

from base_view import BaseView


class StocksView(BaseView):
    """株価データ取得用ビュークラス."""

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

    def get(self) -> Response:
        """指定された銘柄の株価データを取得して返す.

        URLパラメータからsymbolsを取得し、株価データをフェッチして返す.

        Returns:
            株価データを含むJSONレスポンス
        """
        # URLパラメータから銘柄リストを取得
        symbols = self._parse_symbols_parameter()

        stock_data = self.app.fetcher.get_stock_data(symbols)

        return jsonify(
            {
                "timestamp": datetime.now().isoformat(),
                "symbols": symbols,
                "data": stock_data,
            }
        )
