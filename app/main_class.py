import tomllib
import logging
from pathlib import Path
from flask import jsonify
from flask.views import MethodView
from stock_fetcher import StockDataFetcher

logger = logging.getLogger(__name__)


class Main(MethodView):
    """メインアプリケーションクラス"""

    def __init__(self):
        self.app_info = self.get_app_info()
        self.name = self.app_info["name"]
        self.version = self.app_info["version"]
        self.description = self.app_info["description"]

    def initialize_fetcher(self, stock_fetch_duration, stock_fetch_errors):
        """StockDataFetcherインスタンスを初期化"""
        self.fetcher = StockDataFetcher(
            stock_fetch_duration=stock_fetch_duration,
            stock_fetch_errors=stock_fetch_errors,
        )

    def get_version(self):
        """pyproject.tomlからバージョンを取得"""
        try:
            # 現在のファイルと同じディレクトリのpyproject.tomlを読み込み
            pyproject_path = Path(__file__).parent / "pyproject.toml"

            if not pyproject_path.exists():
                return 1

            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
                return data.get("project", {}).get("version", "unknown")
        except Exception as e:
            print(f"Error reading version from pyproject.toml: {e}")
            return 1

    def get_app_info(self):
        """アプリケーション情報を取得"""
        try:
            pyproject_path = Path(__file__).parent / "pyproject.toml"

            if not pyproject_path.exists():
                return {
                    "name": "stockvalue-exporter",
                    "version": "unknown",
                    "description": "Unknown",
                }

            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
                project = data.get("project", {})
                return {
                    "name": project.get("name", "stockvalue-exporter"),
                    "version": project.get("version", "unknown"),
                    "description": project.get(
                        "description", "Stock value exporter for Prometheus"
                    ),
                }
        except Exception as e:
            print(f"Error reading app info from pyproject.toml: {e}")
            return {
                "name": "stockvalue-exporter",
                "version": "unknown",
                "description": "Unknown",
            }


    def get(self):
        """ヘルスチェック（ルート "/" 用）"""
        return f"{self.name} v{self.version} is running!"

