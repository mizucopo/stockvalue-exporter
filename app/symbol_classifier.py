"""シンボル分類ユーティリティモジュール."""

from enum import Enum
from typing import Final


class AssetType(Enum):
    """資産タイプの列挙型."""

    STOCK = "stock"
    FOREX = "forex"
    INDEX = "index"
    CRYPTO = "crypto"


class SymbolClassifier:
    """金融シンボルの分類を行うユーティリティクラス."""

    # パフォーマンス向上のため、セットを使用してO(1)検索を実現
    _KNOWN_CRYPTOCURRENCIES: Final[set[str]] = {
        "BTC-USD",
        "ETH-USD",
        "ADA-USD",
        "XRP-USD",
        "SOL-USD",
        "DOGE-USD",
        "DOT-USD",
        "MATIC-USD",
        "LTC-USD",
        "BCH-USD",
        "LINK-USD",
        "XLM-USD",
        "ALGO-USD",
        "ATOM-USD",
        "AVAX-USD",
    }

    _KNOWN_JAPANESE_INDICES: Final[set[str]] = {"998405.T"}  # TOPIX

    @classmethod
    def is_forex_pair(cls, symbol: str) -> bool:
        """シンボルが為替ペアかどうかを判定する.

        Args:
            symbol: 判定するシンボル

        Returns:
            為替ペアならTrue、そうでなければFalse
        """
        return symbol.endswith("=X")

    @classmethod
    def is_index(cls, symbol: str) -> bool:
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
        return symbol in cls._KNOWN_JAPANESE_INDICES

    @classmethod
    def is_crypto(cls, symbol: str) -> bool:
        """シンボルが暗号通貨かどうかを判定する.

        Args:
            symbol: 判定するシンボル

        Returns:
            暗号通貨ならTrue、そうでなければFalse
        """
        return symbol in cls._KNOWN_CRYPTOCURRENCIES

    @classmethod
    def get_asset_type(cls, symbol: str) -> AssetType:
        """シンボルの資産タイプを取得する.

        Args:
            symbol: 判定するシンボル

        Returns:
            対応するAssetType
        """
        if cls.is_forex_pair(symbol):
            return AssetType.FOREX
        elif cls.is_index(symbol):
            return AssetType.INDEX
        elif cls.is_crypto(symbol):
            return AssetType.CRYPTO
        else:
            return AssetType.STOCK

    @classmethod
    def get_currency_for_symbol(cls, symbol: str) -> str:
        """シンボルに対応する通貨を取得する.

        Args:
            symbol: 通貨を取得するシンボル

        Returns:
            通貨コード
        """
        # USDJPY=X の場合はJPY
        if symbol == "USDJPY=X":
            return "JPY"

        # 日本の指数の場合はJPY
        if symbol in ["^N225", "998405.T"]:
            return "JPY"

        # その他はUSDがデフォルト
        return "USD"

    @classmethod
    def get_exchange_for_symbol(cls, symbol: str) -> str:
        """シンボルに対応する取引所を取得する.

        Args:
            symbol: 取引所を取得するシンボル

        Returns:
            取引所名
        """
        asset_type = cls.get_asset_type(symbol)

        if asset_type == AssetType.FOREX:
            return "FX"
        elif asset_type == AssetType.INDEX:
            return "INDEX"
        elif asset_type == AssetType.CRYPTO:
            return "CRYPTO"
        else:
            return "Unknown"  # 株式の場合はAPI情報を使用

    @classmethod
    def add_crypto_symbol(cls, symbol: str) -> None:
        """新しい暗号通貨シンボルを追加する.

        Args:
            symbol: 追加する暗号通貨シンボル

        Note:
            実行時にセットを変更するため、慎重に使用すること
        """
        cls._KNOWN_CRYPTOCURRENCIES.add(symbol)

    @classmethod
    def add_index_symbol(cls, symbol: str) -> None:
        """新しい指数シンボルを追加する.

        Args:
            symbol: 追加する指数シンボル

        Note:
            実行時にセットを変更するため、慎重に使用すること
        """
        cls._KNOWN_JAPANESE_INDICES.add(symbol)
