"""アプリケーションメインクラスモジュール."""

import logging
import tomllib
from pathlib import Path
from typing import Any

from flask.views import MethodView
from prometheus_client import Counter, Histogram

from stock_fetcher import StockDataFetcher

logger = logging.getLogger(__name__)


class App(MethodView):
    """アプリケーションクラス."""

    def __init__(self) -> None:
        """アプリケーションインスタンスを初期化する."""
        self.app_info = self.get_app_info()
        self.name = self.app_info["name"]
        self.version = self.app_info["version"]
        self.description = self.app_info["description"]
        self.metrics_factory: Any | None = None

    def set_metrics_factory(self, metrics_factory: Any) -> None:  # noqa: ANN401
        """MetricsFactoryインスタンスを設定する.

        Args:
            metrics_factory: MetricsFactoryインスタンス
        """
        self.metrics_factory = metrics_factory

    def initialize_fetcher(
        self, stock_fetch_duration: Histogram, stock_fetch_errors: Counter
    ) -> None:
        """StockDataFetcherインスタンスを初期化する."""
        self.fetcher = StockDataFetcher(
            stock_fetch_duration=stock_fetch_duration,
            stock_fetch_errors=stock_fetch_errors,
        )

    def get_version(self) -> str | int:
        """pyproject.tomlからバージョンを取得する."""
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

    def get_app_info(self) -> dict[str, str]:
        """アプリケーション情報を取得する."""
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

    def get(self) -> str:
        """ヘルスチェック（ルート '/' 用）.

        Returns:
            アプリケーションの稼働状況を示すメッセージ
        """
        return f"{self.name} v{self.version} is running!"
