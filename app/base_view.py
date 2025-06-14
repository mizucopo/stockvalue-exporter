"""ベースビュークラスモジュール."""

from typing import TYPE_CHECKING, Protocol

from flask import request
from flask.views import MethodView

from config import config

if TYPE_CHECKING:
    from metrics_view import MetricsFactoryProtocol
    from stock_fetcher import StockDataFetcher


class AppProtocol(Protocol):
    """アプリケーションインスタンスのプロトコル."""

    name: str
    version: str
    description: str
    fetcher: "StockDataFetcher"

    @property
    def metrics_factory(self) -> "MetricsFactoryProtocol":
        """MetricsFactoryインスタンスを取得する."""
        ...


class BaseView(MethodView):
    """すべてのViewクラスの基底クラス."""

    # クラス変数でアプリケーションインスタンスを保持
    _app_instance: AppProtocol | None = None

    @classmethod
    def set_app_instance(cls, app_instance: AppProtocol) -> None:
        """全てのビューに使用するアプリケーションインスタンスを設定する.

        Args:
            app_instance: アプリケーションインスタンス
        """
        cls._app_instance = app_instance

    @classmethod
    def is_app_instance_set(cls) -> bool:
        """アプリケーションインスタンスが設定されているかチェックする.

        Returns:
            アプリケーションインスタンスが設定されている場合True
        """
        return cls._app_instance is not None

    def __init__(self, app_instance: AppProtocol | None = None) -> None:
        """ベースビューを初期化する.

        Args:
            app_instance: Flaskアプリケーションインスタンス

        Raises:
            RuntimeError: アプリケーションインスタンスが設定されていない場合
        """
        if app_instance is not None:
            self.app = app_instance
        elif self._app_instance is not None:
            self.app = self._app_instance
        else:
            raise RuntimeError(
                "App instance not set. Call BaseView.set_app_instance(app) during application setup."
            )

    def _parse_symbols_parameter(self) -> list[str]:
        """URLパラメータからsymbolsを解析して銘柄リストを返す.

        以下の形式をサポート:
        - ?symbols=AAPL,GOOGL (カンマ区切り文字列)
        - ?symbols=AAPL&symbols=GOOGL (配列形式)
        - ?symbols=AAPL,GOOGL&symbols=MSFT (混合形式)

        フォールバック動作:
        - パラメータが存在しない場合: デフォルトシンボルを返す
        - パラメータが存在するが空の場合: デフォルトシンボルを返す
        - 有効なシンボルが提供された場合: 提供されたシンボルを返す

        Note:
            空のsymbolsパラメータ（?symbols= や ?symbols=,, など）は
            デフォルトシンボルにフォールバックします。これにより
            一貫した動作を保証し、空のリクエストを防ぎます。

        Returns:
            正規化された銘柄リスト（常に1つ以上のシンボルを含む）

        Raises:
            ValueError: シンボルが無効な場合（形式、長さ、数量制限違反）
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

        # フォールバック処理：空のリストの場合はデフォルトを使用
        # これにより ?symbols= や ?symbols=,, などの空パラメータに対して
        # 一貫した動作を提供する
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
