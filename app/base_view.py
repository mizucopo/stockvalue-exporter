from flask.views import MethodView


class BaseView(MethodView):
    """すべてのViewクラスの基底クラス"""

    def __init__(self):
        # main_appは後でインポート時に設定される
        from main import main_app

        self.main_app = main_app
