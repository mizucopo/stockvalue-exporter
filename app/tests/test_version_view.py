"""VersionViewクラスのテストモジュール."""

import json
from unittest.mock import Mock, patch

from version_view import VersionView


class TestVersionView:
    """VersionViewクラスのテストケース."""

    def test_get_method(self, app_context):
        """getメソッドをテストする."""
        # モックアプリケーションインスタンスを作成
        mock_app = Mock()
        mock_app.name = "version-test-app"
        mock_app.version = "3.1.4"
        mock_app.description = "Version test application"

        with patch("main.app", mock_app):
            version_view = VersionView()
            response = version_view.get()

            # JSONレスポンスを確認
            assert response.status_code == 200
            assert response.content_type == "application/json"

            # レスポンスデータを確認
            data = json.loads(response.get_data(as_text=True))
            expected_data = {
                "name": "version-test-app",
                "version": "3.1.4",
                "description": "Version test application",
            }
            assert data == expected_data

    def test_inheritance_from_base_view(self):
        """BaseViewからの継承をテストする."""
        from base_view import BaseView

        assert issubclass(VersionView, BaseView)

    def test_app_access(self):
        """appインスタンスへのアクセスをテストする."""
        mock_app = Mock()
        mock_app.name = "version-app"
        mock_app.version = "1.2.3"
        mock_app.description = "Version app description"

        with patch("main.app", mock_app):
            version_view = VersionView()

            # appインスタンスが正しく設定されているか確認
            assert version_view.app == mock_app
            assert version_view.app.name == "version-app"
            assert version_view.app.version == "1.2.3"
            assert version_view.app.description == "Version app description"

    def test_response_format(self, app_context):
        """レスポンス形式をテストする."""
        mock_app = Mock()
        mock_app.name = "format-test"
        mock_app.version = "0.1.0"
        mock_app.description = "Format test"

        with patch("main.app", mock_app):
            version_view = VersionView()
            response = version_view.get()

            # レスポンスがFlaskのResponseオブジェクトであることを確認
            from flask import Response

            assert isinstance(response, Response)

            # Content-Typeヘッダーを確認
            assert response.headers["Content-Type"] == "application/json"
