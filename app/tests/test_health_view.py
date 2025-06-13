"""HealthViewクラスのテストモジュール."""

import json
from unittest.mock import Mock

from flask import Flask

from health_view import HealthView


class TestHealthView:
    """HealthViewクラスのテストケース."""

    def test_get_method(self, app_context: Flask) -> None:
        """getメソッドをテストする."""
        # モックアプリケーションインスタンスを作成
        mock_app = Mock()
        mock_app.name = "stockvalue-exporter"
        mock_app.version = "2.1.0"
        mock_app.description = "A Prometheus custom exporter for real-time stock price monitoring and metrics collection"

        health_view = HealthView(app_instance=mock_app)
        response = health_view.get()

        # JSONレスポンスを確認
        assert response.status_code == 200
        assert response.content_type == "application/json"

        # レスポンスデータを確認
        data = json.loads(response.get_data(as_text=True))
        expected_data = {
            "name": "stockvalue-exporter",
            "version": "2.1.0",
            "description": "A Prometheus custom exporter for real-time stock price monitoring and metrics collection",
            "status": "running",
            "message": "stockvalue-exporter v2.1.0 is running!",
        }
        assert data == expected_data

    def test_inheritance_from_base_view(self) -> None:
        """BaseViewからの継承をテストする."""
        from base_view import BaseView

        assert issubclass(HealthView, BaseView)

    def test_app_access(self) -> None:
        """appインスタンスへのアクセスをテストする."""
        mock_app = Mock()
        mock_app.name = "health-test"
        mock_app.version = "2.0.0"
        mock_app.description = "Health test app"

        health_view = HealthView(app_instance=mock_app)

        # appインスタンスが正しく設定されているか確認
        assert health_view.app == mock_app
        assert health_view.app.name == "health-test"
        assert health_view.app.version == "2.0.0"
        assert health_view.app.description == "Health test app"
