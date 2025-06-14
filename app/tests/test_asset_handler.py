"""AssetHandlerとStrategyパターンのテスト."""

import pytest

from asset_handler import (
    AssetHandler,
    AssetHandlerFactory,
    CryptoHandler,
    ForexHandler,
    IndexHandler,
    StockHandler,
)
from symbol_classifier import AssetType


class TestStockHandler:
    """StockHandlerクラスのテスト."""

    def test_stock_handler_methods(self) -> None:
        """株式ハンドラーの各メソッドをテストする."""
        handler = StockHandler()

        assert handler.get_price_metric_key() == "stock_price"
        assert handler.get_volume_metric_key() == "stock_volume"
        assert handler.get_market_cap_metric_key() == "stock_market_cap"
        assert handler.get_range_metric_keys() == (
            "stock_52week_high",
            "stock_52week_low",
        )
        assert handler.get_change_metric_keys() == (
            "stock_previous_close",
            "stock_price_change",
            "stock_price_change_percent",
        )
        assert handler.get_timestamp_metric_key() == "stock_last_updated"
        assert handler.get_error_metric_key() == "stock_fetch_errors"
        assert handler.should_update_volume() is True
        assert handler.should_update_market_metrics() is True

        additional = handler.get_additional_metrics()
        assert additional == {}


class TestForexHandler:
    """ForexHandlerクラスのテスト."""

    def test_forex_handler_methods(self) -> None:
        """為替ハンドラーの各メソッドをテストする."""
        handler = ForexHandler()

        assert handler.get_price_metric_key() == "forex_rate"
        assert handler.get_volume_metric_key() is None
        assert handler.get_market_cap_metric_key() is None
        assert handler.get_range_metric_keys() == (
            "forex_52week_high",
            "forex_52week_low",
        )
        assert handler.get_change_metric_keys() == (
            "forex_previous_close",
            "forex_rate_change",
            "forex_rate_change_percent",
        )
        assert handler.get_timestamp_metric_key() == "forex_last_updated"
        assert handler.get_error_metric_key() == "forex_fetch_errors"
        assert handler.should_update_volume() is False
        assert handler.should_update_market_metrics() is False
        assert handler.get_additional_metrics() == {}


class TestIndexHandler:
    """IndexHandlerクラスのテスト."""

    def test_index_handler_methods(self) -> None:
        """指数ハンドラーの各メソッドをテストする."""
        handler = IndexHandler()

        assert handler.get_price_metric_key() == "index_value"
        assert handler.get_volume_metric_key() == "index_volume"
        assert handler.get_market_cap_metric_key() is None
        assert handler.get_range_metric_keys() == (
            "index_52week_high",
            "index_52week_low",
        )
        assert handler.get_change_metric_keys() == (
            "index_previous_close",
            "index_value_change",
            "index_value_change_percent",
        )
        assert handler.get_timestamp_metric_key() == "index_last_updated"
        assert handler.get_error_metric_key() == "index_fetch_errors"
        assert handler.should_update_volume() is True
        assert handler.should_update_market_metrics() is False
        assert handler.get_additional_metrics() == {}


class TestCryptoHandler:
    """CryptoHandlerクラスのテスト."""

    def test_crypto_handler_methods(self) -> None:
        """暗号通貨ハンドラーの各メソッドをテストする."""
        handler = CryptoHandler()

        assert handler.get_price_metric_key() == "crypto_price"
        assert handler.get_volume_metric_key() == "crypto_volume"
        assert handler.get_market_cap_metric_key() == "crypto_market_cap"
        assert handler.get_range_metric_keys() == (
            "crypto_52week_high",
            "crypto_52week_low",
        )
        assert handler.get_change_metric_keys() == (
            "crypto_previous_close",
            "crypto_price_change",
            "crypto_price_change_percent",
        )
        assert handler.get_timestamp_metric_key() == "crypto_last_updated"
        assert handler.get_error_metric_key() == "crypto_fetch_errors"
        assert handler.should_update_volume() is True
        assert handler.should_update_market_metrics() is True
        assert handler.get_additional_metrics() == {}


class TestAssetHandlerFactory:
    """AssetHandlerFactoryクラスのテスト."""

    def test_get_stock_handler(self) -> None:
        """株式ハンドラー取得をテストする."""
        handler = AssetHandlerFactory.get_handler(AssetType.STOCK)
        assert isinstance(handler, StockHandler)

    def test_get_forex_handler(self) -> None:
        """為替ハンドラー取得をテストする."""
        handler = AssetHandlerFactory.get_handler(AssetType.FOREX)
        assert isinstance(handler, ForexHandler)

    def test_get_index_handler(self) -> None:
        """指数ハンドラー取得をテストする."""
        handler = AssetHandlerFactory.get_handler(AssetType.INDEX)
        assert isinstance(handler, IndexHandler)

    def test_get_crypto_handler(self) -> None:
        """暗号通貨ハンドラー取得をテストする."""
        handler = AssetHandlerFactory.get_handler(AssetType.CRYPTO)
        assert isinstance(handler, CryptoHandler)

    def test_unsupported_asset_type(self) -> None:
        """未サポートの資産タイプでValueErrorが発生することをテストする."""

        # 存在しない資産タイプを無理やり作成してテスト
        class FakeAssetType:
            pass

        with pytest.raises(ValueError, match="Unsupported asset type"):
            AssetHandlerFactory.get_handler(FakeAssetType())  # type: ignore[arg-type]

    def test_same_instance_returned(self) -> None:
        """同じ資産タイプに対して同じインスタンスが返されることをテストする."""
        handler1 = AssetHandlerFactory.get_handler(AssetType.STOCK)
        handler2 = AssetHandlerFactory.get_handler(AssetType.STOCK)
        assert handler1 is handler2


class TestAssetHandlerAbstractMethods:
    """AssetHandlerの抽象メソッドのテスト."""

    def test_abstract_methods_cannot_instantiate(self) -> None:
        """AssetHandlerは抽象クラスなのでインスタンス化できないことをテストする."""
        with pytest.raises(TypeError):
            AssetHandler()  # type: ignore[abstract]

    def test_concrete_handlers_implement_all_methods(self) -> None:
        """具象ハンドラーが全ての抽象メソッドを実装していることをテストする."""
        handlers = [StockHandler(), ForexHandler(), IndexHandler(), CryptoHandler()]

        for handler in handlers:
            # 全ての抽象メソッドが実装されていることを確認
            assert hasattr(handler, "get_price_metric_key")
            assert hasattr(handler, "get_volume_metric_key")
            assert hasattr(handler, "get_market_cap_metric_key")
            assert hasattr(handler, "get_range_metric_keys")
            assert hasattr(handler, "get_change_metric_keys")
            assert hasattr(handler, "get_timestamp_metric_key")
            assert hasattr(handler, "get_error_metric_key")
            assert hasattr(handler, "should_update_volume")
            assert hasattr(handler, "should_update_market_metrics")
            assert hasattr(handler, "get_additional_metrics")

            # メソッドが呼び出し可能であることを確認
            assert callable(handler.get_price_metric_key)
            assert callable(handler.get_volume_metric_key)
            assert callable(handler.get_market_cap_metric_key)
            assert callable(handler.get_range_metric_keys)
            assert callable(handler.get_change_metric_keys)
            assert callable(handler.get_timestamp_metric_key)
            assert callable(handler.get_error_metric_key)
            assert callable(handler.should_update_volume)
            assert callable(handler.should_update_market_metrics)
            assert callable(handler.get_additional_metrics)


class TestHandlerReturnTypes:
    """ハンドラーの戻り値の型をテストする."""

    @pytest.mark.parametrize(
        "handler_class", [StockHandler, ForexHandler, IndexHandler, CryptoHandler]
    )
    def test_return_types(self, handler_class: type[AssetHandler]) -> None:
        """各ハンドラーの戻り値の型をテストする."""
        handler = handler_class()

        # 文字列を返すメソッド
        assert isinstance(handler.get_price_metric_key(), str)
        assert isinstance(handler.get_timestamp_metric_key(), str)
        assert isinstance(handler.get_error_metric_key(), str)

        # 文字列またはNoneを返すメソッド
        volume_key = handler.get_volume_metric_key()
        assert volume_key is None or isinstance(volume_key, str)

        market_cap_key = handler.get_market_cap_metric_key()
        assert market_cap_key is None or isinstance(market_cap_key, str)

        # タプルを返すメソッド
        range_keys = handler.get_range_metric_keys()
        assert isinstance(range_keys, tuple)
        assert len(range_keys) == 2
        assert all(isinstance(key, str) for key in range_keys)

        change_keys = handler.get_change_metric_keys()
        assert isinstance(change_keys, tuple)
        assert len(change_keys) == 3
        assert all(isinstance(key, str) for key in change_keys)

        # ブール値を返すメソッド
        assert isinstance(handler.should_update_volume(), bool)
        assert isinstance(handler.should_update_market_metrics(), bool)

        # 辞書を返すメソッド
        additional = handler.get_additional_metrics()
        assert isinstance(additional, dict)
        assert all(
            isinstance(k, str) and isinstance(v, str) for k, v in additional.items()
        )
