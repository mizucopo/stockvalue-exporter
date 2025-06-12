"""HealthViewクラスのテストモジュール."""

import json
from unittest.mock import Mock, patch

from health_view import HealthView


class TestHealthView:
    """HealthViewクラスのテストケース."""

    def test_get_method(self, app_context):
        """getメソッドをテストする."""
        # モックアプリケーションインスタンスを作成
        mock_app = Mock()
        mock_app.name = "test-app"
        mock_app.version = "1.0.0"
        mock_app.description = "Test application"

        with patch("main.app", mock_app):
            health_view = HealthView()
            response = health_view.get()

            # JSONレスポンスを確認
            assert response.status_code == 200
            assert response.content_type == "application/json"

            # レスポンスデータを確認
            data = json.loads(response.get_data(as_text=True))
            expected_data = {
                "name": "test-app",
                "version": "1.0.0",
                "description": "Test application",
                "status": "running",
                "message": "test-app v1.0.0 is running!",
            }
            assert data == expected_data

    def test_inheritance_from_base_view(self):
        """BaseViewからの継承をテストする."""
        from base_view import BaseView

        assert issubclass(HealthView, BaseView)

    def test_app_access(self):
        """appインスタンスへのアクセスをテストする."""
        mock_app = Mock()
        mock_app.name = "health-test"
        mock_app.version = "2.0.0"
        mock_app.description = "Health test app"

        with patch("main.app", mock_app):
            health_view = HealthView()

            # appインスタンスが正しく設定されているか確認
            assert health_view.app == mock_app
            assert health_view.app.name == "health-test"
            assert health_view.app.version == "2.0.0"
            assert health_view.app.description == "Health test app"
