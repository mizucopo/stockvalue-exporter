"""BaseViewクラスのテストモジュール."""

from unittest.mock import Mock, patch

from base_view import BaseView


class TestBaseView:
    """BaseViewクラスのテストケース."""

    def test_init(self):
        """BaseViewクラスの初期化をテストする."""
        mock_app = Mock()
        mock_app.name = "test-app"

        with patch("main.app", mock_app):
            base_view = BaseView()
            assert base_view.app == mock_app

    def test_inheritance_from_method_view(self):
        """MethodViewからの継承をテストする."""
        from flask.views import MethodView

        assert issubclass(BaseView, MethodView)

    def test_parse_symbols_parameter_forex_pair(self, request_context):
        """為替ペアシンボルの解析をテストする."""
        mock_app = Mock()
        with patch("main.app", mock_app):
            base_view = BaseView()

            # Flask test clientでリクエストを模擬
            with patch("base_view.request") as mock_request:
                mock_request.args.getlist.return_value = ["USDJPY=X"]
                mock_request.args.__contains__.return_value = True

                result = base_view._parse_symbols_parameter()
                assert result == ["USDJPY=X"]

    def test_parse_symbols_parameter_mixed_symbols(self, request_context):
        """株式と為替ペアの混合シンボルの解析をテストする."""
        mock_app = Mock()
        with patch("main.app", mock_app):
            base_view = BaseView()

            # Flask test clientでリクエストを模擬
            with patch("base_view.request") as mock_request:
                mock_request.args.getlist.return_value = ["AAPL,USDJPY=X,GOOGL"]
                mock_request.args.__contains__.return_value = True

                result = base_view._parse_symbols_parameter()
                assert result == ["AAPL", "USDJPY=X", "GOOGL"]

    def test_parse_symbols_parameter_multiple_forex_pairs(self, request_context):
        """複数の為替ペアシンボルの解析をテストする."""
        mock_app = Mock()
        with patch("main.app", mock_app):
            base_view = BaseView()

            # Flask test clientでリクエストを模擬
            with patch("base_view.request") as mock_request:
                mock_request.args.getlist.return_value = ["USDJPY=X,EURJPY=X,GBPJPY=X"]
                mock_request.args.__contains__.return_value = True

                result = base_view._parse_symbols_parameter()
                assert result == ["USDJPY=X", "EURJPY=X", "GBPJPY=X"]
