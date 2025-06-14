"""バージョン情報ビューモジュール."""

from flask import Response, jsonify

from base_view import BaseView


class VersionView(BaseView):
    """バージョン情報表示用ビュークラス."""

    def get(self) -> Response:
        """アプリケーションのバージョン情報を返す.

        Returns:
            アプリケーションのバージョン情報を含むJSONレスポンス
        """
        return jsonify(
            {
                "name": self.app.name,
                "version": self.app.version,
                "description": self.app.description,
            }
        )
