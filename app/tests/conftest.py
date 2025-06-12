"""テスト設定ファイル."""

import pytest
from flask import Flask
from prometheus_client import REGISTRY, CollectorRegistry


@pytest.fixture
def app():
    """テスト用Flaskアプリケーション."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def app_context(app):
    """Flaskアプリケーションコンテキスト."""
    with app.app_context():
        yield app


@pytest.fixture
def clean_registry():
    """Prometheusメトリクスレジストリをクリーンアップ."""
    # テスト前の状態を保存
    collectors = list(REGISTRY._collector_to_names.keys())
    yield
    # テスト後にレジストリをクリーンアップ
    for collector in list(REGISTRY._collector_to_names.keys()):
        if collector not in collectors:
            REGISTRY.unregister(collector)


@pytest.fixture
def isolated_registry():
    """各テスト用に独立したPrometheusレジストリを提供."""
    registry = CollectorRegistry()
    yield registry


@pytest.fixture
def request_context(app):
    """Flaskリクエストコンテキスト."""
    with app.test_request_context():
        yield
