from flask.views import MethodView


class BaseView(MethodView):
    """すべてのViewクラスの基底クラス"""

    def __init__(self):
        # appは後でインポート時に設定される
        from main import app

        self.app = app
