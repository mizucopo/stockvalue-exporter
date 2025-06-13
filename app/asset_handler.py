"""資産タイプ別処理用のStrategyパターン実装."""

from abc import ABC, abstractmethod
from typing import Any

from symbol_classifier import AssetType


class AssetHandler(ABC):
    """資産処理の基底クラス."""

    @abstractmethod
    def get_price_metric_key(self) -> str:
        """価格メトリクスのキーを取得する."""
        pass

    @abstractmethod
    def get_volume_metric_key(self) -> str | None:
        """出来高メトリクスのキーを取得する（為替の場合はNone）."""
        pass

    @abstractmethod
    def get_market_cap_metric_key(self) -> str | None:
        """時価総額メトリクスのキーを取得する（為替・指数の場合はNone）."""
        pass

    @abstractmethod
    def get_range_metric_keys(self) -> tuple[str, str]:
        """52週レンジメトリクスのキーを取得する（high, low）."""
        pass

    @abstractmethod
    def get_change_metric_keys(self) -> tuple[str, str, str]:
        """価格変動メトリクスのキーを取得する（close, change, change_percent）."""
        pass

    @abstractmethod
    def get_timestamp_metric_key(self) -> str:
        """タイムスタンプメトリクスのキーを取得する."""
        pass

    @abstractmethod
    def get_error_metric_key(self) -> str:
        """エラーメトリクスのキーを取得する."""
        pass

    @abstractmethod
    def should_update_volume(self) -> bool:
        """出来高メトリクスを更新すべきかどうか."""
        pass

    @abstractmethod
    def should_update_market_metrics(self) -> bool:
        """市場関連メトリクス（時価総額、PER、配当利回り）を更新すべきかどうか."""
        pass

    @abstractmethod
    def get_additional_metrics(self) -> dict[str, Any]:
        """追加の資産タイプ固有メトリクス."""
        pass


class StockHandler(AssetHandler):
    """株式用のハンドラー."""

    def get_price_metric_key(self) -> str:
        return "stock_price"

    def get_volume_metric_key(self) -> str | None:
        return "stock_volume"

    def get_market_cap_metric_key(self) -> str | None:
        return "stock_market_cap"

    def get_range_metric_keys(self) -> tuple[str, str]:
        return ("stock_52week_high", "stock_52week_low")

    def get_change_metric_keys(self) -> tuple[str, str, str]:
        return (
            "stock_previous_close",
            "stock_price_change",
            "stock_price_change_percent",
        )

    def get_timestamp_metric_key(self) -> str:
        return "stock_last_updated"

    def get_error_metric_key(self) -> str:
        return "stock_fetch_errors"

    def should_update_volume(self) -> bool:
        return True

    def should_update_market_metrics(self) -> bool:
        return True

    def get_additional_metrics(self) -> dict[str, Any]:
        return {"stock_pe_ratio": "pe_ratio", "stock_dividend_yield": "dividend_yield"}


class ForexHandler(AssetHandler):
    """為替用のハンドラー."""

    def get_price_metric_key(self) -> str:
        return "forex_rate"

    def get_volume_metric_key(self) -> str | None:
        return None  # 為替は出来高なし

    def get_market_cap_metric_key(self) -> str | None:
        return None  # 為替は時価総額なし

    def get_range_metric_keys(self) -> tuple[str, str]:
        return ("forex_52week_high", "forex_52week_low")

    def get_change_metric_keys(self) -> tuple[str, str, str]:
        return (
            "forex_previous_close",
            "forex_rate_change",
            "forex_rate_change_percent",
        )

    def get_timestamp_metric_key(self) -> str:
        return "forex_last_updated"

    def get_error_metric_key(self) -> str:
        return "forex_fetch_errors"

    def should_update_volume(self) -> bool:
        return False

    def should_update_market_metrics(self) -> bool:
        return False

    def get_additional_metrics(self) -> dict[str, Any]:
        return {}


class IndexHandler(AssetHandler):
    """指数用のハンドラー."""

    def get_price_metric_key(self) -> str:
        return "index_value"

    def get_volume_metric_key(self) -> str | None:
        return "index_volume"

    def get_market_cap_metric_key(self) -> str | None:
        return None  # 指数は時価総額なし

    def get_range_metric_keys(self) -> tuple[str, str]:
        return ("index_52week_high", "index_52week_low")

    def get_change_metric_keys(self) -> tuple[str, str, str]:
        return (
            "index_previous_close",
            "index_value_change",
            "index_value_change_percent",
        )

    def get_timestamp_metric_key(self) -> str:
        return "index_last_updated"

    def get_error_metric_key(self) -> str:
        return "index_fetch_errors"

    def should_update_volume(self) -> bool:
        return True

    def should_update_market_metrics(self) -> bool:
        return False

    def get_additional_metrics(self) -> dict[str, Any]:
        return {}


class CryptoHandler(AssetHandler):
    """暗号通貨用のハンドラー."""

    def get_price_metric_key(self) -> str:
        return "crypto_price"

    def get_volume_metric_key(self) -> str | None:
        return "crypto_volume"

    def get_market_cap_metric_key(self) -> str | None:
        return "crypto_market_cap"

    def get_range_metric_keys(self) -> tuple[str, str]:
        return ("crypto_52week_high", "crypto_52week_low")

    def get_change_metric_keys(self) -> tuple[str, str, str]:
        return (
            "crypto_previous_close",
            "crypto_price_change",
            "crypto_price_change_percent",
        )

    def get_timestamp_metric_key(self) -> str:
        return "crypto_last_updated"

    def get_error_metric_key(self) -> str:
        return "crypto_fetch_errors"

    def should_update_volume(self) -> bool:
        return True

    def should_update_market_metrics(self) -> bool:
        return True  # 暗号通貨は時価総額あり、PER・配当利回りなし

    def get_additional_metrics(self) -> dict[str, Any]:
        return {}


class AssetHandlerFactory:
    """資産ハンドラーのファクトリークラス."""

    _handlers = {
        AssetType.STOCK: StockHandler(),
        AssetType.FOREX: ForexHandler(),
        AssetType.INDEX: IndexHandler(),
        AssetType.CRYPTO: CryptoHandler(),
    }

    @classmethod
    def get_handler(cls, asset_type: AssetType) -> AssetHandler:
        """指定された資産タイプのハンドラーを取得する.

        Args:
            asset_type: 資産タイプ

        Returns:
            対応するAssetHandler

        Raises:
            ValueError: 未サポートの資産タイプの場合
        """
        if asset_type not in cls._handlers:
            raise ValueError(f"Unsupported asset type: {asset_type}")

        return cls._handlers[asset_type]
