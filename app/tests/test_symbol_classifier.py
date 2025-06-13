"""SymbolClassifierのテスト."""

from symbol_classifier import AssetType, SymbolClassifier


class TestSymbolClassifier:
    """SymbolClassifierクラスのテストクラス."""

    def test_is_forex_pair_true(self):
        """為替ペアの正しい判定をテストする."""
        assert SymbolClassifier.is_forex_pair("USDJPY=X") is True
        assert SymbolClassifier.is_forex_pair("EURJPY=X") is True
        assert SymbolClassifier.is_forex_pair("GBPJPY=X") is True
        assert SymbolClassifier.is_forex_pair("AUDJPY=X") is True

    def test_is_forex_pair_false(self):
        """為替ペアでないシンボルの判定をテストする."""
        assert SymbolClassifier.is_forex_pair("AAPL") is False
        assert SymbolClassifier.is_forex_pair("GOOGL") is False
        assert SymbolClassifier.is_forex_pair("BRK-B") is False
        assert SymbolClassifier.is_forex_pair("5255.T") is False
        assert SymbolClassifier.is_forex_pair("^GSPC") is False
        assert SymbolClassifier.is_forex_pair("BTC-USD") is False

    def test_is_index_true(self):
        """株価指数の正しい判定をテストする."""
        assert SymbolClassifier.is_index("^GSPC") is True
        assert SymbolClassifier.is_index("^NDX") is True
        assert SymbolClassifier.is_index("^N225") is True
        assert SymbolClassifier.is_index("998405.T") is True
        assert SymbolClassifier.is_index("^IXIC") is True

    def test_is_index_false(self):
        """株価指数でないシンボルの判定をテストする."""
        assert SymbolClassifier.is_index("AAPL") is False
        assert SymbolClassifier.is_index("GOOGL") is False
        assert SymbolClassifier.is_index("USDJPY=X") is False
        assert SymbolClassifier.is_index("BRK-B") is False
        assert SymbolClassifier.is_index("5255.T") is False  # 通常の日本株
        assert SymbolClassifier.is_index("BTC-USD") is False

    def test_is_crypto_true(self):
        """暗号通貨の正しい判定をテストする."""
        assert SymbolClassifier.is_crypto("BTC-USD") is True
        assert SymbolClassifier.is_crypto("ETH-USD") is True
        assert SymbolClassifier.is_crypto("ADA-USD") is True
        assert SymbolClassifier.is_crypto("XRP-USD") is True
        assert SymbolClassifier.is_crypto("SOL-USD") is True

    def test_is_crypto_false(self):
        """暗号通貨でないシンボルの判定をテストする."""
        assert SymbolClassifier.is_crypto("AAPL") is False
        assert SymbolClassifier.is_crypto("GOOGL") is False
        assert SymbolClassifier.is_crypto("USDJPY=X") is False
        assert SymbolClassifier.is_crypto("^GSPC") is False
        assert SymbolClassifier.is_crypto("BRK-B") is False
        assert SymbolClassifier.is_crypto("5255.T") is False

    def test_get_asset_type_stock(self):
        """株式アセットタイプの取得をテストする."""
        assert SymbolClassifier.get_asset_type("AAPL") == AssetType.STOCK
        assert SymbolClassifier.get_asset_type("GOOGL") == AssetType.STOCK
        assert SymbolClassifier.get_asset_type("BRK-B") == AssetType.STOCK
        assert SymbolClassifier.get_asset_type("5255.T") == AssetType.STOCK

    def test_get_asset_type_forex(self):
        """為替アセットタイプの取得をテストする."""
        assert SymbolClassifier.get_asset_type("USDJPY=X") == AssetType.FOREX
        assert SymbolClassifier.get_asset_type("EURJPY=X") == AssetType.FOREX
        assert SymbolClassifier.get_asset_type("GBPJPY=X") == AssetType.FOREX

    def test_get_asset_type_index(self):
        """指数アセットタイプの取得をテストする."""
        assert SymbolClassifier.get_asset_type("^GSPC") == AssetType.INDEX
        assert SymbolClassifier.get_asset_type("^N225") == AssetType.INDEX
        assert SymbolClassifier.get_asset_type("998405.T") == AssetType.INDEX

    def test_get_asset_type_crypto(self):
        """暗号通貨アセットタイプの取得をテストする."""
        assert SymbolClassifier.get_asset_type("BTC-USD") == AssetType.CRYPTO
        assert SymbolClassifier.get_asset_type("ETH-USD") == AssetType.CRYPTO
        assert SymbolClassifier.get_asset_type("ADA-USD") == AssetType.CRYPTO

    def test_get_currency_for_symbol(self):
        """シンボルの通貨取得をテストする."""
        # 特定の為替ペア
        assert SymbolClassifier.get_currency_for_symbol("USDJPY=X") == "JPY"

        # 日本の指数
        assert SymbolClassifier.get_currency_for_symbol("^N225") == "JPY"
        assert SymbolClassifier.get_currency_for_symbol("998405.T") == "JPY"

        # その他（デフォルトUSD）
        assert SymbolClassifier.get_currency_for_symbol("AAPL") == "USD"
        assert SymbolClassifier.get_currency_for_symbol("BTC-USD") == "USD"
        assert SymbolClassifier.get_currency_for_symbol("^GSPC") == "USD"

    def test_get_exchange_for_symbol(self):
        """シンボルの取引所取得をテストする."""
        # 為替
        assert SymbolClassifier.get_exchange_for_symbol("USDJPY=X") == "FX"

        # 指数
        assert SymbolClassifier.get_exchange_for_symbol("^GSPC") == "INDEX"
        assert SymbolClassifier.get_exchange_for_symbol("^N225") == "INDEX"

        # 暗号通貨
        assert SymbolClassifier.get_exchange_for_symbol("BTC-USD") == "CRYPTO"

        # 株式（Unknown - API情報を使用）
        assert SymbolClassifier.get_exchange_for_symbol("AAPL") == "Unknown"

    def test_add_crypto_symbol(self):
        """暗号通貨シンボルの動的追加をテストする."""
        new_crypto = "NEW-USD"

        # 追加前は認識されない
        assert SymbolClassifier.is_crypto(new_crypto) is False
        assert SymbolClassifier.get_asset_type(new_crypto) == AssetType.STOCK

        # 追加
        SymbolClassifier.add_crypto_symbol(new_crypto)

        # 追加後は認識される
        assert SymbolClassifier.is_crypto(new_crypto) is True
        assert SymbolClassifier.get_asset_type(new_crypto) == AssetType.CRYPTO

    def test_add_index_symbol(self):
        """指数シンボルの動的追加をテストする."""
        new_index = "999999.T"

        # 追加前は認識されない
        assert SymbolClassifier.is_index(new_index) is False
        assert SymbolClassifier.get_asset_type(new_index) == AssetType.STOCK

        # 追加
        SymbolClassifier.add_index_symbol(new_index)

        # 追加後は認識される
        assert SymbolClassifier.is_index(new_index) is True
        assert SymbolClassifier.get_asset_type(new_index) == AssetType.INDEX

    def test_performance_crypto_lookup(self):
        """暗号通貨のセット検索パフォーマンステスト."""
        # 大量のテストでも高速に処理されることを確認
        for _ in range(1000):
            assert SymbolClassifier.is_crypto("BTC-USD") is True
            assert SymbolClassifier.is_crypto("AAPL") is False

    def test_asset_type_enum_values(self):
        """AssetTypeの列挙値をテストする."""
        assert AssetType.STOCK.value == "stock"
        assert AssetType.FOREX.value == "forex"
        assert AssetType.INDEX.value == "index"
        assert AssetType.CRYPTO.value == "crypto"
