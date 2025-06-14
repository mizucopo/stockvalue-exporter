"""テスト設定ファイル."""

from collections.abc import Generator

import pytest
from flask import Flask
from prometheus_client import REGISTRY, CollectorRegistry


@pytest.fixture
def app() -> Flask:
    """テスト用Flaskアプリケーション."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def app_context(app: Flask) -> Generator[Flask]:
    """Flaskアプリケーションコンテキスト."""
    with app.app_context():
        yield app


@pytest.fixture
def clean_registry() -> Generator[None]:
    """Prometheusメトリクスレジストリをクリーンアップ."""
    # テスト前の状態を保存
    collectors = list(REGISTRY._collector_to_names.keys())
    yield
    # テスト後にレジストリをクリーンアップ
    for collector in list(REGISTRY._collector_to_names.keys()):
        if collector not in collectors:
            REGISTRY.unregister(collector)


@pytest.fixture
def isolated_registry() -> Generator[CollectorRegistry]:
    """各テスト用に独立したPrometheusレジストリを提供."""
    registry = CollectorRegistry()
    yield registry


@pytest.fixture
def request_context(app: Flask) -> Generator[None]:
    """Flaskリクエストコンテキスト."""
    with app.test_request_context():
        yield
