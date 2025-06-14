"""Appクラスのテストモジュール."""

from unittest.mock import mock_open, patch

from app import App


class TestApp:
    """Appクラスのテストケース."""

    def test_init(self) -> None:
        """Appクラスの初期化をテストする."""
        with patch.object(App, "get_app_info") as mock_get_app_info:
            mock_get_app_info.return_value = {
                "name": "test-app",
                "version": "1.0.0",
                "description": "Test application",
            }

            app = App()

            assert app.name == "test-app"
            assert app.version == "1.0.0"
            assert app.description == "Test application"
            mock_get_app_info.assert_called_once()

    def test_get_version_success(self) -> None:
        """バージョン取得成功をテストする."""
        mock_data = b"""
[project]
name = "test-app"
version = "1.2.3"
description = "Test"
"""
        with patch("builtins.open", mock_open(read_data=mock_data)):
            with patch("pathlib.Path.exists", return_value=True):
                app = App()
                version = app.get_version()
                assert version == "1.2.3"

    def test_get_version_file_not_found(self) -> None:
        """pyproject.tomlが存在しない場合をテストする."""
        with patch("pathlib.Path.exists", return_value=False):
            app = App()
            version = app.get_version()
            assert version == "unknown"

    def test_get_version_exception(self) -> None:
        """バージョン取得時の例外をテストする."""
        with patch("builtins.open", side_effect=Exception("File error")):
            with patch("pathlib.Path.exists", return_value=True):
                app = App()
                version = app.get_version()
                assert version == "unknown"

    def test_get_version_return_type_consistency(self) -> None:
        """get_versionメソッドが常に文字列を返すことをテストする."""
        app = App()

        # 成功時の文字列型確認
        mock_data = b"""
[project]
name = "test-app"
version = "1.2.3"
"""
        with patch("builtins.open", mock_open(read_data=mock_data)):
            with patch("pathlib.Path.exists", return_value=True):
                version = app.get_version()
                assert isinstance(version, str)
                assert version == "1.2.3"

        # ファイル不存在時の文字列型確認
        with patch("pathlib.Path.exists", return_value=False):
            version = app.get_version()
            assert isinstance(version, str)
            assert version == "unknown"

        # 例外時の文字列型確認
        with patch("builtins.open", side_effect=Exception("File error")):
            with patch("pathlib.Path.exists", return_value=True):
                version = app.get_version()
                assert isinstance(version, str)
                assert version == "unknown"

    def test_version_string_formatting_compatibility(self) -> None:
        """バージョンが文字列フォーマッティングで問題なく使用できることをテストする."""
        app = App()

        # ファイル不存在時でも文字列フォーマッティングが可能
        with patch("pathlib.Path.exists", return_value=False):
            version = app.get_version()
            formatted = f"v{version}"
            assert formatted == "vunknown"

        # 成功時も文字列フォーマッティングが可能
        mock_data = b"""
[project]
version = "1.2.3"
"""
        with patch("builtins.open", mock_open(read_data=mock_data)):
            with patch("pathlib.Path.exists", return_value=True):
                version = app.get_version()
                formatted = f"v{version}"
                assert formatted == "v1.2.3"

    def test_get_app_info_success(self) -> None:
        """アプリケーション情報取得成功をテストする."""
        mock_data = b"""
[project]
name = "stockvalue-exporter"
version = "2.0.0"
description = "Stock value exporter"
"""
        with patch("builtins.open", mock_open(read_data=mock_data)):
            with patch("pathlib.Path.exists", return_value=True):
                app = App()
                info = app.get_app_info()

                assert info["name"] == "stockvalue-exporter"
                assert info["version"] == "2.0.0"
                assert info["description"] == "Stock value exporter"

    def test_get_app_info_file_not_found(self) -> None:
        """pyproject.tomlが存在しない場合のデフォルト値をテストする."""
        with patch("pathlib.Path.exists", return_value=False):
            app = App()
            info = app.get_app_info()

            assert info["name"] == "stockvalue-exporter"
            assert info["version"] == "unknown"
            assert info["description"] == "Unknown"

    def test_get_app_info_exception(self) -> None:
        """アプリケーション情報取得時の例外をテストする."""
        with patch("builtins.open", side_effect=Exception("File error")):
            with patch("pathlib.Path.exists", return_value=True):
                app = App()
                info = app.get_app_info()

                assert info["name"] == "stockvalue-exporter"
                assert info["version"] == "unknown"
                assert info["description"] == "Unknown"

    def test_get_method(self) -> None:
        """getメソッドをテストする."""
        with patch.object(App, "get_app_info") as mock_get_app_info:
            mock_get_app_info.return_value = {
                "name": "test-app",
                "version": "1.0.0",
                "description": "Test application",
            }

            app = App()
            result = app.get()

            assert result == "test-app v1.0.0 is running!"

    def test_initialize_fetcher(self) -> None:
        """initialize_fetcherメソッドをテストする."""
        from unittest.mock import Mock

        with patch.object(App, "get_app_info") as mock_get_app_info:
            mock_get_app_info.return_value = {
                "name": "test-app",
                "version": "1.0.0",
                "description": "Test application",
            }

            app = App()

            mock_duration = Mock()
            mock_errors = Mock()

            with patch("app.StockDataFetcher") as mock_fetcher:
                app.initialize_fetcher(mock_duration, mock_errors)

                mock_fetcher.assert_called_once_with(
                    financial_fetch_duration=mock_duration,
                    financial_fetch_errors=mock_errors,
                )
                assert app.fetcher == mock_fetcher.return_value
