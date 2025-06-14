"""VersionViewクラスのテストモジュール."""

import json
from unittest.mock import Mock

from flask import Flask

from version_view import VersionView


class TestVersionView:
    """VersionViewクラスのテストケース."""

    def test_get_method(self, app_context: Flask) -> None:
        """getメソッドをテストする."""
        # モックアプリケーションインスタンスを作成
        mock_app = Mock()
        mock_app.name = "stockvalue-exporter"
        mock_app.version = "2.1.0"
        mock_app.description = "A Prometheus custom exporter for real-time stock price monitoring and metrics collection"

        version_view = VersionView(app_instance=mock_app)
        response = version_view.get()

        # JSONレスポンスを確認
        assert response.status_code == 200
        assert response.content_type == "application/json"

        # レスポンスデータを確認
        data = json.loads(response.get_data(as_text=True))
        expected_data = {
            "name": "stockvalue-exporter",
            "version": "2.1.0",
            "description": "A Prometheus custom exporter for real-time stock price monitoring and metrics collection",
        }
        assert data == expected_data

    def test_inheritance_from_base_view(self) -> None:
        """BaseViewからの継承をテストする."""
        from base_view import BaseView

        assert issubclass(VersionView, BaseView)

    def test_app_access(self) -> None:
        """appインスタンスへのアクセスをテストする."""
        mock_app = Mock()
        mock_app.name = "version-app"
        mock_app.version = "1.2.3"
        mock_app.description = "Version app description"

        version_view = VersionView(app_instance=mock_app)

        # appインスタンスが正しく設定されているか確認
        assert version_view.app == mock_app
        assert version_view.app.name == "version-app"
        assert version_view.app.version == "1.2.3"
        assert version_view.app.description == "Version app description"

    def test_response_format(self, app_context: Flask) -> None:
        """レスポンス形式をテストする."""
        mock_app = Mock()
        mock_app.name = "format-test"
        mock_app.version = "0.1.0"
        mock_app.description = "Format test"

        version_view = VersionView(app_instance=mock_app)
        response = version_view.get()

        # レスポンスがFlaskのResponseオブジェクトであることを確認
        from flask import Response

        assert isinstance(response, Response)

        # Content-Typeヘッダーを確認
        assert response.headers["Content-Type"] == "application/json"
