"""設定管理モジュール."""

import os


class Config:
    """アプリケーション設定を管理するクラス."""

    def __init__(self) -> None:
        """設定を初期化する."""
        self._load_config()

    def _load_config(self) -> None:
        """環境変数から設定を読み込む."""
        # サーバー設定
        self.HOST = os.getenv("HOST", "0.0.0.0")
        self.PORT = int(os.getenv("PORT", "9100"))
        self.DEBUG = os.getenv("DEBUG", "false").lower() == "true"

        # ログ設定
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

        # 株価関連設定
        self.DEFAULT_SYMBOLS = self._parse_symbols_env(
            os.getenv("DEFAULT_SYMBOLS", "AAPL,GOOGL,MSFT,TSLA")
        )
        self.CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "600"))
        self.MAX_SYMBOLS_PER_REQUEST = int(os.getenv("MAX_SYMBOLS_PER_REQUEST", "10"))

        # API設定
        self.REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
        self.MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

        # キャッシュ設定
        self.CACHE_MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", "100"))

    def _parse_symbols_env(self, symbols_str: str) -> list[str]:
        """環境変数からシンボルリストを解析する.
        
        Args:
            symbols_str: カンマ区切りのシンボル文字列
            
        Returns:
            シンボルのリスト
        """
        return [symbol.strip().upper() for symbol in symbols_str.split(",") if symbol.strip()]

    @property
    def is_production(self) -> bool:
        """本番環境かどうかを判定する.
        
        Returns:
            本番環境の場合True
        """
        return os.getenv("ENVIRONMENT", "development").lower() == "production"

    def get_cache_key(self, symbols: list[str]) -> str:
        """キャッシュキーを生成する.
        
        Args:
            symbols: シンボルのリスト
            
        Returns:
            キャッシュキー
        """
        return f"stock_data:{'_'.join(sorted(symbols))}"

    def validate_symbols(self, symbols: list[str]) -> bool:
        """シンボルの妥当性を検証する.
        
        Args:
            symbols: 検証するシンボルのリスト
            
        Returns:
            すべてのシンボルが有効な場合True
        """
        if not symbols:
            return False

        if len(symbols) > self.MAX_SYMBOLS_PER_REQUEST:
            return False

        for symbol in symbols:
            # 基本的な形式チェック（英数字、1-10文字）
            if not symbol.isalnum() or len(symbol) < 1 or len(symbol) > 10:
                return False

        return True


# グローバル設定インスタンス
config = Config()
