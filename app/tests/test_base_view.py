"""BaseViewクラスのテストモジュール."""

from collections.abc import Generator
from unittest.mock import MagicMock, Mock, patch

import pytest

from base_view import BaseView


class TestBaseView:
    """BaseViewクラスのテストケース."""

    def test_init(self) -> None:
        """BaseViewクラスの初期化をテストする."""
        mock_app = Mock()
        mock_app.name = "test-app"

        # BaseViewインスタンスを直接アプリで初期化
        base_view = BaseView(app_instance=mock_app)
        assert base_view.app == mock_app

    def test_inheritance_from_method_view(self) -> None:
        """MethodViewからの継承をテストする."""
        from flask.views import MethodView

        assert issubclass(BaseView, MethodView)

    def test_parse_symbols_parameter_forex_pair(
        self, request_context: Generator[None]
    ) -> None:
        """為替ペアシンボルの解析をテストする."""
        mock_app = Mock()
        base_view = BaseView(app_instance=mock_app)

        # Flask test clientでリクエストを模擬
        with patch("base_view.request") as mock_request:
            mock_args = MagicMock()
            mock_args.getlist.return_value = ["USDJPY=X"]
            mock_args.__contains__ = lambda self, key: key == "symbols"
            mock_request.args = mock_args

            result = base_view._parse_symbols_parameter()
            assert result == ["USDJPY=X"]

    def test_parse_symbols_parameter_mixed_symbols(
        self, request_context: Generator[None]
    ) -> None:
        """株式と為替ペアの混合シンボルの解析をテストする."""
        mock_app = Mock()
        base_view = BaseView(app_instance=mock_app)

        # Flask test clientでリクエストを模擬
        with patch("base_view.request") as mock_request:
            mock_args = MagicMock()
            mock_args.getlist.return_value = ["AAPL,USDJPY=X,GOOGL"]
            mock_args.__contains__ = lambda self, key: key == "symbols"
            mock_request.args = mock_args

            result = base_view._parse_symbols_parameter()
            assert result == ["AAPL", "USDJPY=X", "GOOGL"]

    def test_parse_symbols_parameter_multiple_forex_pairs(
        self, request_context: Generator[None]
    ) -> None:
        """複数の為替ペアシンボルの解析をテストする."""
        mock_app = Mock()
        base_view = BaseView(app_instance=mock_app)

        # Flask test clientでリクエストを模擬
        with patch("base_view.request") as mock_request:
            mock_args = MagicMock()
            mock_args.getlist.return_value = ["USDJPY=X,EURJPY=X,GBPJPY=X"]
            mock_args.__contains__ = lambda self, key: key == "symbols"
            mock_request.args = mock_args

            result = base_view._parse_symbols_parameter()
            assert result == ["USDJPY=X", "EURJPY=X", "GBPJPY=X"]

    def test_set_app_instance(self) -> None:
        """set_app_instanceメソッドをテストする."""
        mock_app = Mock()
        mock_app.name = "test-app"

        # クラスメソッドでインスタンスを設定
        BaseView.set_app_instance(mock_app)
        assert BaseView._app_instance == mock_app

        # 新しいインスタンスでも設定されたアプリが使用される
        base_view = BaseView()
        assert base_view.app == mock_app

        # クリーンアップ
        BaseView._app_instance = None

    def test_is_app_instance_set(self) -> None:
        """is_app_instance_setメソッドをテストする."""
        # 初期状態ではFalse
        BaseView._app_instance = None
        assert BaseView.is_app_instance_set() is False

        # インスタンスを設定後はTrue
        mock_app = Mock()
        BaseView.set_app_instance(mock_app)
        assert BaseView.is_app_instance_set() is True

        # クリーンアップ
        BaseView._app_instance = None

    def test_init_without_app_instance_raises_error(self) -> None:
        """アプリインスタンスが設定されていない場合にエラーが発生することをテストする."""
        # クラス変数をNoneにリセット
        BaseView._app_instance = None

        with pytest.raises(RuntimeError, match="App instance not set"):
            BaseView()

    def test_init_with_class_app_instance(self) -> None:
        """クラスアプリインスタンスが設定されている場合の初期化をテストする."""
        mock_app = Mock()
        mock_app.name = "test-app"

        # クラスレベルでアプリインスタンスを設定
        BaseView.set_app_instance(mock_app)

        # 個別のapp_instanceを指定しなくても初期化できる
        base_view = BaseView()
        assert base_view.app == mock_app

        # クリーンアップ
        BaseView._app_instance = None

    def test_init_individual_app_instance_overrides_class_instance(self) -> None:
        """個別のアプリインスタンスがクラスインスタンスを上書きすることをテストする."""
        class_app = Mock()
        class_app.name = "class-app"
        individual_app = Mock()
        individual_app.name = "individual-app"

        # クラスレベルでアプリインスタンスを設定
        BaseView.set_app_instance(class_app)

        # 個別のapp_instanceを指定して初期化
        base_view = BaseView(app_instance=individual_app)
        assert base_view.app == individual_app
        assert base_view.app != class_app

        # クリーンアップ
        BaseView._app_instance = None
