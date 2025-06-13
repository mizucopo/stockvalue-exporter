"""ベースビュークラスモジュール."""

from typing import Any

from flask import request
from flask.views import MethodView

from config import config


class BaseView(MethodView):
    """すべてのViewクラスの基底クラス."""

    # クラス変数でアプリケーションインスタンスを保持
    _app_instance: Any | None = None

    @classmethod
    def set_app_instance(cls, app_instance: Any) -> None:
        """全てのビューに使用するアプリケーションインスタンスを設定する.

        Args:
            app_instance: アプリケーションインスタンス
        """
        cls._app_instance = app_instance

    def __init__(self, app_instance: Any | None = None) -> None:
        """ベースビューを初期化する.

        Args:
            app_instance: Flaskアプリケーションインスタンス
        """
        if app_instance is not None:
            self.app = app_instance
        elif self._app_instance is not None:
            self.app = self._app_instance
        else:
            # 後方互換性のためのフォールバック（循環インポート）
            from main import app

            self.app = app

    def _parse_symbols_parameter(self) -> list[str]:
        """URLパラメータからsymbolsを解析して銘柄リストを返す.

        以下の形式をサポート:
        - ?symbols=AAPL,GOOGL (カンマ区切り文字列)
        - ?symbols=AAPL&symbols=GOOGL (配列形式)
        - ?symbols=AAPL,GOOGL&symbols=MSFT (混合形式)

        Returns:
            正規化された銘柄リスト

        Raises:
            ValueError: シンボルが無効な場合
        """
        # URLパラメータから全ての symbols 値を取得
        symbols_list = request.args.getlist("symbols")

        # symbols パラメータが全く存在しない場合
        if "symbols" not in request.args:
            return config.DEFAULT_SYMBOLS.copy()

        # 全てのパラメータ値を処理
        symbols = []
        for param_value in symbols_list:
            if param_value:
                # カンマ区切りの可能性を考慮して分割
                split_symbols = [
                    s.strip().upper() for s in param_value.split(",") if s.strip()
                ]
                symbols.extend(split_symbols)

        # 効率的な重複除去（順序保持）
        unique_symbols = list(dict.fromkeys(symbols))

        # フォールバック処理
        final_symbols = (
            unique_symbols if unique_symbols else config.DEFAULT_SYMBOLS.copy()
        )

        # 入力検証
        if not config.validate_symbols(final_symbols):
            raise ValueError(
                f"Invalid symbols provided. Max {config.MAX_SYMBOLS_PER_REQUEST} symbols allowed, "
                f"each must be 1-15 characters (alphanumeric, periods, hyphens). Received: {final_symbols}"
            )

        return final_symbols
