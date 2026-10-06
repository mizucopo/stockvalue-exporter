"""VersionViewクラスのテストモジュール."""

import json
from unittest.mock import Mock, mock_open, patch

import pytest
from flask import Flask

from src.app import App
from src.version_view import VersionView


class TestVersionView:
    """VersionViewクラスのテストケース."""

    @pytest.mark.parametrize(
        ("file_exists", "metadata", "version", "description"),
        [
            pytest.param(
                True,
                b'[project]\nname = "stockvalue-exporter"\nversion = "1.2.3"\n'
                b'description = "Test exporter"\n',
                "1.2.3",
                "Test exporter",
                id="valid-metadata",
            ),
            pytest.param(False, b"", "unknown", "Unknown", id="missing-file"),
            pytest.param(True, b"[project", "unknown", "Unknown", id="invalid-toml"),
        ],
    )
    def test_version_and_root_metadata(
        self,
        app: Flask,
        file_exists: bool,
        metadata: bytes,
        version: str,
        description: str,
    ) -> None:
        """実メタデータ取得と失敗時の両HTTP表示を検証する."""
        with (
            patch("src.app.Path.exists", return_value=file_exists),
            patch("builtins.open", mock_open(read_data=metadata)),
        ):
            app_instance = App()
            app.add_url_rule("/", view_func=App.as_view("main"))
            app.add_url_rule(
                "/version",
                view_func=VersionView.as_view("version", app_instance=app_instance),
            )
            client = app.test_client()

            version_response = client.get("/version")
            assert version_response.status_code == 200
            assert version_response.content_type == "application/json"
            assert version_response.get_json() == {
                "name": "stockvalue-exporter",
                "version": version,
                "description": description,
            }

            root_response = client.get("/")
            assert root_response.status_code == 200
            assert root_response.get_data(as_text=True) == (
                f"stockvalue-exporter v{version} is running!"
            )

    def test_get_method(self, app_context: Flask) -> None:
        """getメソッドをテストする."""
        # モックアプリケーションインスタンスを作成
        mock_app = Mock()
        mock_app.name = "stockvalue-exporter"
        mock_app.version = "2.1.0"
        mock_app.description = (
            "A Prometheus custom exporter for real-time stock price monitoring "
            "and metrics collection"
        )

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
            "description": (
                "A Prometheus custom exporter for real-time stock price monitoring "
                "and metrics collection"
            ),
        }
        assert data == expected_data

    def test_inheritance_from_base_view(self) -> None:
        """BaseViewからの継承をテストする."""
        from src.base_view import BaseView

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
