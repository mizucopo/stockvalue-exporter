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
