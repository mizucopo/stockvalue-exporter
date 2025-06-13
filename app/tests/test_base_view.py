"""BaseViewクラスのテストモジュール."""

from collections.abc import Generator
from unittest.mock import MagicMock, Mock, patch

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
